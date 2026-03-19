#!/bin/bash
#SBATCH --job-name=claim-extract
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:l40s:2
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/claim_extraction/scripts_slurm/logs/claim_extract_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/claim_extraction/scripts_slurm/logs/claim_extract_%j.err

set -euo pipefail

# Always use the repository root, not the submit directory
# Use SLURM_SUBMIT_DIR (where sbatch was called from) instead of BASH_SOURCE
# to avoid issues with SLURM copying scripts to /var/spool/slurm/
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  SCRIPT_DIR="${SLURM_SUBMIT_DIR}"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

# Clean cache
find "${ROOT_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

# Ensure Python imports from current directory first
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

LOG_DIR="${ROOT_DIR}/claim_extraction/scripts_slurm/logs"
mkdir -p "${LOG_DIR}"

# Required parameters
MODEL="${MODEL:-hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4}"
CONFIG_FILE="${CONFIG_FILE:-claim_extraction/configs/claim_extraction_llama70b.yaml}"
INSTANCES_FILE="${INSTANCES_FILE:-claim_extraction/instances.json}"
OUTPUT_DIR="${OUTPUT_DIR:-claim_extraction/claims_out}"

# Optional parameters
LIMIT="${LIMIT:-}"
MIN_SCORE="${MIN_SCORE:-}"
PORT="${PORT:-8000}"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: Unable to locate a python interpreter. Set PYTHON_BIN in the sbatch export list." >&2
  exit 3
fi

# Port management functions
is_port_free() {
  "${PYTHON_BIN}" - "$1" <<'PY'
import socket, sys
port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        raise SystemExit(1)
raise SystemExit(0)
PY
}

find_free_port() {
  "${PYTHON_BIN}" <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

if ! is_port_free "${PORT}"; then
  NEW_PORT="$(find_free_port)"
  echo "Port ${PORT} occupied; switching to ${NEW_PORT}." >&2
  PORT="${NEW_PORT}"
fi

ENDPOINT="http://127.0.0.1:${PORT}/v1"

module load cuda/12.6.3 2>/dev/null || true

# Set HuggingFace cache to cml-scratch
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

# ============================================
# MULTI-GPU CONFIGURATION & AUTO-DETECTION
# ============================================

# Detect GPU count from SLURM allocation
if [[ -n "${SLURM_GPUS_ON_NODE:-}" ]]; then
  GPU_COUNT="${SLURM_GPUS_ON_NODE}"
elif [[ -n "${SLURM_JOB_GPUS:-}" ]]; then
  GPU_COUNT=$(echo "${SLURM_JOB_GPUS}" | tr ',' '\n' | wc -l)
else
  GPU_COUNT="${GPU_COUNT:-1}"
fi

# Detect model size to optimize parameters
MODEL_SIZE="unknown"
if [[ "${MODEL}" =~ deepseek-coder-v2-instruct ]]; then
  MODEL_SIZE="70b"  # Treat DeepSeek-V2 (236B MoE) like 70B for memory config
elif [[ "${MODEL}" =~ Qwen2.5-72B ]]; then
  MODEL_SIZE="72b"  # Qwen 72B
elif [[ "${MODEL}" =~ 70[Bb] ]]; then
  MODEL_SIZE="70b"
elif [[ "${MODEL}" =~ Qwen3 ]]; then
  MODEL_SIZE="32b"
elif [[ "${MODEL}" =~ (32[Bb]|33[Bb]) ]]; then
  MODEL_SIZE="32b"
elif [[ "${MODEL}" =~ (7[Bb]|8[Bb]) ]]; then
  MODEL_SIZE="small"
fi

# Configure vLLM parameters based on GPU count and model size
TENSOR_PARALLEL_SIZE="${GPU_COUNT}"

if [[ ${GPU_COUNT} -ge 4 ]]; then
  # 4+ GPUs: Maximum throughput configuration
  GPU_MEM_UTIL=0.85
  if [[ "${MODEL_SIZE}" == "70b" || "${MODEL_SIZE}" == "72b" ]]; then
    MAX_MODEL_LEN=12288
    MAX_NUM_SEQS=128
  else
    MAX_MODEL_LEN=16384
    MAX_NUM_SEQS=256
  fi
  ENABLE_CHUNKED_PREFILL="true"

elif [[ ${GPU_COUNT} -ge 2 ]]; then
  # 2-3 GPUs: Balanced configuration (RECOMMENDED for 70B/72B)
  GPU_MEM_UTIL=0.90
  if [[ "${MODEL_SIZE}" == "70b" || "${MODEL_SIZE}" == "72b" ]]; then
    MAX_MODEL_LEN=8192
    MAX_NUM_SEQS=64
  else
    MAX_MODEL_LEN=12288
    MAX_NUM_SEQS=128
  fi
  ENABLE_CHUNKED_PREFILL="false"

else
  # 1 GPU: Memory-constrained configuration
  GPU_MEM_UTIL=0.95
  if [[ "${MODEL_SIZE}" == "70b" || "${MODEL_SIZE}" == "72b" ]]; then
    MAX_MODEL_LEN=4096
    MAX_NUM_SEQS=32
    ENFORCE_EAGER="true"
  else
    MAX_MODEL_LEN=8192
    MAX_NUM_SEQS=64
    ENFORCE_EAGER="false"
  fi
  ENABLE_CHUNKED_PREFILL="false"
fi

# Allow manual overrides via environment variables
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-${MAX_MODEL_LEN}}"
GPU_MEM_UTIL="${VLLM_GPU_MEMORY_UTIL:-${GPU_MEM_UTIL}}"
MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-${MAX_NUM_SEQS}}"

# PyTorch memory optimization for large models
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

echo "========================================="
echo "Multi-GPU Claim Extraction"
echo "========================================="
echo "Node: $(hostname -s)"
echo "Model: ${MODEL}"
echo "Config: ${CONFIG_FILE}"
echo "Instances: ${INSTANCES_FILE}"
echo "Output: ${OUTPUT_DIR}"
echo ""
echo "GPU Configuration:"
echo "  GPUs: ${GPU_COUNT}"
echo "  Tensor Parallel Size: ${TENSOR_PARALLEL_SIZE}"
echo "  Model Size Detected: ${MODEL_SIZE}"
echo "  GPU Memory Util: ${GPU_MEM_UTIL}"
echo "  Max Model Length: ${MAX_MODEL_LEN}"
echo "  Max Num Seqs: ${MAX_NUM_SEQS}"
if [[ "${ENFORCE_EAGER:-false}" == "true" ]]; then
  echo "  Enforce Eager: enabled (memory saving)"
fi
echo ""

# Start vLLM server
echo "Starting vLLM with ${MODEL} on ${ENDPOINT}..."
echo "  Configuration: ${GPU_COUNT} GPU(s), max_len=${MAX_MODEL_LEN}, mem_util=${GPU_MEM_UTIL}"

# Build vLLM arguments dynamically
VLLM_SERVER_ARGS=(
  --model "${MODEL}"
  --host 127.0.0.1
  --port ${PORT}
  --gpu-memory-utilization ${GPU_MEM_UTIL}
  --max-model-len ${MAX_MODEL_LEN}
  --max-num-seqs ${MAX_NUM_SEQS}
  --dtype auto
  --trust-remote-code
)

# Add tensor parallelism for multi-GPU
if [[ ${GPU_COUNT} -gt 1 ]]; then
  VLLM_SERVER_ARGS+=(--tensor-parallel-size ${TENSOR_PARALLEL_SIZE})
fi

# vLLM 0.8.5+ auto-detects quantization from model config (awq, awq_marlin, etc.)

# Enable eager mode for memory-constrained single GPU 70B
if [[ "${ENFORCE_EAGER:-false}" == "true" ]]; then
  VLLM_SERVER_ARGS+=(--enforce-eager)
  echo "  Eager execution enabled (CUDA graphs disabled for memory saving)"
fi

# Enable chunked prefill for high-throughput 4+ GPU setups
if [[ "${ENABLE_CHUNKED_PREFILL:-false}" == "true" ]]; then
  VLLM_SERVER_ARGS+=(--enable-chunked-prefill)
  echo "  Chunked prefill enabled for higher throughput"
fi

PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  "${VLLM_SERVER_ARGS[@]}" \
  > "${LOG_DIR}/vllm_claim_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

# Wait for vLLM readiness
if [[ "${MODEL}" =~ deepseek-coder-v2-instruct ]]; then
  MAX_WAIT_ITERATIONS=300  # 10 minutes for DeepSeek-V2 (120GB model)
  echo "Waiting for vLLM readiness (DeepSeek-V2 120GB model, may take 5-10 minutes)..."
elif [[ "${MODEL_SIZE}" == "70b" || "${MODEL_SIZE}" == "72b" ]]; then
  MAX_WAIT_ITERATIONS=210  # 7 minutes for 70B models (includes V1 graph compilation)
  echo "Waiting for vLLM readiness (70B+ model, may take 4-7 minutes)..."
else
  MAX_WAIT_ITERATIONS=180  # 6 minutes for smaller models (V1 engine graph compilation)
  echo "Waiting for vLLM readiness (may take 3-6 minutes with V1 engine)..."
fi

for i in $(seq 1 ${MAX_WAIT_ITERATIONS}); do
  if curl -s -f "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "✓ vLLM ready after ~$((i * 2)) seconds"
    break
  fi
  if [[ $((i % 15)) -eq 0 ]]; then
    echo "  Still waiting... ($((i * 2))s elapsed)"
  fi
  sleep 2
done

if ! curl -s -f "${ENDPOINT}/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM did not start within $((MAX_WAIT_ITERATIONS * 2)) seconds. Tail of log:"
  tail -n 120 "${LOG_DIR}/vllm_claim_${SLURM_JOB_ID}.log" || true
  kill ${VLLM_PID} || true
  exit 1
fi

# ============================================
# RUN CLAIM EXTRACTION
# ============================================
echo ""
echo "========================================="
echo "Starting Claim Extraction"
echo "========================================="

# Update config file endpoint dynamically
TEMP_CONFIG="${LOG_DIR}/config_${SLURM_JOB_ID}.yaml"
sed "s|endpoint:.*|endpoint: ${ENDPOINT}|g" "${CONFIG_FILE}" > "${TEMP_CONFIG}"

# Build claim extraction arguments
CLAIM_ARGS=(
  --config "${TEMP_CONFIG}"
  --input "${INSTANCES_FILE}"
  --out "${OUTPUT_DIR}"
  --model-name "${MODEL}"
)

if [[ -n "${LIMIT}" ]]; then
  CLAIM_ARGS+=(--limit "${LIMIT}")
fi

if [[ -n "${MIN_SCORE}" ]]; then
  CLAIM_ARGS+=(--min-score "${MIN_SCORE}")
fi

set +e
PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m claim_extraction.cli \
  "${CLAIM_ARGS[@]}"

EXTRACTION_EXIT=$?
set -e

# Clean up temp config
rm -f "${TEMP_CONFIG}"

echo ""
echo "========================================="
echo "Results"
echo "========================================="
if [[ ${EXTRACTION_EXIT} -eq 0 ]]; then
  echo "✓ Claim extraction complete"

  # Extract model slug for output path
  MODEL_SLUG=$(echo "${MODEL}" | sed 's|.*/||' | sed 's/[^a-zA-Z0-9._-]/-/g')
  SUMMARY_FILE="${OUTPUT_DIR}/${MODEL_SLUG}/summary.json"

  if [[ -f "${SUMMARY_FILE}" ]]; then
    echo ""
    echo "Summary:"
    python3 -c "import json; s=json.load(open('${SUMMARY_FILE}')); print(f\"  Instances: {s['eligibility']['total_instances']}\"); print(f\"  Eligible: {s['eligibility']['eligible']}\"); print(f\"  Total claims: {s['totals']['total_final_claims']}\"); print(f\"  Avg claims/instance: {s['totals']['avg_final_claims_per_eligible_instance']:.2f}\")" 2>/dev/null || cat "${SUMMARY_FILE}"
  fi
else
  echo "✗ Claim extraction failed with exit code ${EXTRACTION_EXIT}"
fi

echo ""
echo "Stopping vLLM..."
kill ${VLLM_PID} || true
wait ${VLLM_PID} || true

echo "Done."
exit ${EXTRACTION_EXIT}
