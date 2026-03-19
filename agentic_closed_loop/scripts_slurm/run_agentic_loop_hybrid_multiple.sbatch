#!/bin/bash
#SBATCH --job-name=agentic-multi
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:rtxa6000:2
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=02:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm/logs/agentic_multi_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm/logs/agentic_multi_%j.err

set -euo pipefail

# Always use the repository root, not the submit directory
# This prevents path duplication when submitting from subdirectories
# Use SLURM_SUBMIT_DIR (where sbatch was called from) instead of BASH_SOURCE
# to avoid issues with SLURM copying scripts to /var/spool/slurm/
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  SCRIPT_DIR="${SLURM_SUBMIT_DIR}"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

#Clean cache
find "${ROOT_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

# Ensure Python imports from current directory first
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

LOG_DIR="${ROOT_DIR}/agentic_closed_loop/scripts_slurm/logs"
mkdir -p "${LOG_DIR}"

INSTANCE_ID="${INSTANCE_ID:-}"
CLAIM_ID="${CLAIM_ID:-C1}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-4}"
TIMEOUT_S="${TIMEOUT_S:-300}"
REPOS_ROOT="${REPOS_ROOT:-/fs/nexus-scratch/ihbas/repos_claim_cache}"
SINGULARITY_IMAGE="${SINGULARITY_IMAGE:-}"

# Auto-detect Singularity image
if [[ -z "${SINGULARITY_IMAGE}" ]]; then
  for candidate in \
    "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif" \
    "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif"; do
    if [[ -f "${candidate}" ]]; then
      SINGULARITY_IMAGE="${candidate}"
      break
    fi
  done
fi

if [[ -z "${INSTANCE_ID}" ]]; then
  echo "ERROR: INSTANCE_ID environment variable is required. Use sbatch --export=INSTANCE_ID=..." >&2
  exit 2
fi

if [[ ! -f "${SINGULARITY_IMAGE}" ]]; then
  echo "ERROR: Singularity image not found at ${SINGULARITY_IMAGE}" >&2
  exit 4
fi

source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

MODEL="${CLAIM_LLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct-AWQ}"
CLAIMS_MODEL="${CLAIMS_MODEL:-${MODEL}}"
TESTS_MODEL="${TESTS_MODEL:-${MODEL}}"
USE_MODEL_SUBDIRS="${USE_MODEL_SUBDIRS:-false}"
PORT="${CLAIM_LLM_PORT:-8000}"

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
  if [[ -n "${CLAIM_LLM_FORCE_PORT:-}" ]]; then
    echo "ERROR: Port ${PORT} busy and CLAIM_LLM_FORCE_PORT set." >&2
    exit 1
  fi
  NEW_PORT="$(find_free_port)"
  echo "Port ${PORT} occupied; switching to ${NEW_PORT}." >&2
  PORT="${NEW_PORT}"
fi

ENDPOINT="http://127.0.0.1:${PORT}/v1"
VLLM_EXTRA_ARGS=()
SERVER_API_KEY="${VLLM_API_KEY:-${CLAIM_LLM_API_KEY:-}}"
if [[ -n "${SERVER_API_KEY}" ]]; then
  export VLLM_API_KEY="${SERVER_API_KEY}"
  export CLAIM_LLM_API_KEY="${SERVER_API_KEY}"
  VLLM_EXTRA_ARGS+=(--api-key "${SERVER_API_KEY}")
fi

module load cuda/12.6.3 2>/dev/null || true

# Set HuggingFace cache to cml-scratch instead of nexus-scratch
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

# ============================================
# MULTI-GPU CONFIGURATION & AUTO-DETECTION
# ============================================

# Detect GPU count from SLURM allocation or environment variable
if [[ -n "${SLURM_GPUS_ON_NODE:-}" ]]; then
  GPU_COUNT="${SLURM_GPUS_ON_NODE}"
elif [[ -n "${SLURM_JOB_GPUS:-}" ]]; then
  # Count comma-separated GPU IDs
  GPU_COUNT=$(echo "${SLURM_JOB_GPUS}" | tr ',' '\n' | wc -l)
else
  GPU_COUNT="${GPU_COUNT:-1}"
fi

# Detect model size to optimize parameters
MODEL_SIZE="unknown"
if [[ "${TESTS_MODEL}" =~ 70[Bb] ]]; then
  MODEL_SIZE="70b"
elif [[ "${TESTS_MODEL}" =~ Qwen3 ]]; then
  MODEL_SIZE="32b"
elif [[ "${TESTS_MODEL}" =~ (32[Bb]|33[Bb]) ]]; then
  MODEL_SIZE="32b"
elif [[ "${TESTS_MODEL}" =~ (7[Bb]|8[Bb]) ]]; then
  MODEL_SIZE="small"
fi

# Configure vLLM parameters based on GPU count and model size
TENSOR_PARALLEL_SIZE="${GPU_COUNT}"

if [[ ${GPU_COUNT} -ge 4 ]]; then
  # 4+ GPUs: Maximum throughput configuration
  GPU_MEM_UTIL=0.85
  if [[ "${MODEL_SIZE}" == "70b" ]]; then
    MAX_MODEL_LEN=12288
    MAX_NUM_SEQS=128
  else
    MAX_MODEL_LEN=16384
    MAX_NUM_SEQS=256
  fi
  ENABLE_CHUNKED_PREFILL="true"

elif [[ ${GPU_COUNT} -ge 2 ]]; then
  # 2-3 GPUs: Balanced configuration (RECOMMENDED for 70B)
  GPU_MEM_UTIL=0.90
  if [[ "${MODEL_SIZE}" == "70b" ]]; then
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
  if [[ "${MODEL_SIZE}" == "70b" ]]; then
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

echo "========================================="
echo "Multi-GPU Agentic Loop Execution"
echo "========================================="
echo "Node: $(hostname -s)"
echo "Instance: ${INSTANCE_ID}"
echo "Claim: ${CLAIM_ID}"
echo "Claims Model: ${CLAIMS_MODEL}"
echo "Tests Model: ${TESTS_MODEL}"
echo "Use Model Subdirs: ${USE_MODEL_SUBDIRS}"
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
echo "Repos root: ${REPOS_ROOT}"
echo "Singularity image: ${SINGULARITY_IMAGE}"
echo ""

# Start vLLM server (outside container)
echo "Starting vLLM with ${TESTS_MODEL} on ${ENDPOINT}..."
echo "  Configuration: ${GPU_COUNT} GPU(s), max_len=${MAX_MODEL_LEN}, mem_util=${GPU_MEM_UTIL}"

# Build vLLM arguments dynamically
VLLM_SERVER_ARGS=(
  --model "${TESTS_MODEL}"
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

# Add any extra args (API key, etc.)
if [[ ${#VLLM_EXTRA_ARGS[@]} -gt 0 ]]; then
  VLLM_SERVER_ARGS+=("${VLLM_EXTRA_ARGS[@]}")
fi

PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  "${VLLM_SERVER_ARGS[@]}" \
  > "${LOG_DIR}/vllm_multi_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

# Wait for vLLM readiness (longer for 70B models)
if [[ "${MODEL_SIZE}" == "70b" ]]; then
  MAX_WAIT_ITERATIONS=210  # 7 minutes for 70B models (includes V1 graph compilation)
  echo "Waiting for vLLM readiness (70B model, may take 4-7 minutes)..."
else
  MAX_WAIT_ITERATIONS=180  # 6 minutes for smaller models (V1 engine graph compilation)
  echo "Waiting for vLLM readiness (may take 3-6 minutes with V1 engine)..."
fi

CURL_ARGS=(-s -f)
if [[ -n "${SERVER_API_KEY}" ]]; then
  CURL_ARGS+=(-H "Authorization: Bearer ${SERVER_API_KEY}")
fi

for i in $(seq 1 ${MAX_WAIT_ITERATIONS}); do
  if curl "${CURL_ARGS[@]}" "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "✓ vLLM ready after ~$((i * 2)) seconds"
    break
  fi
  if [[ $((i % 15)) -eq 0 ]]; then
    echo "  Still waiting... ($((i * 2))s elapsed)"
  fi
  sleep 2
done

if ! curl "${CURL_ARGS[@]}" "${ENDPOINT}/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM did not start within $((MAX_WAIT_ITERATIONS * 2)) seconds. Tail of log:"
  tail -n 120 "${LOG_DIR}/vllm_multi_${SLURM_JOB_ID}.log" || true
  kill ${VLLM_PID} || true
  exit 1
fi

export CLAIM_LLM_BACKEND="vLLM"
export CLAIM_LLM_ENDPOINT="${ENDPOINT}"
export CLAIM_LLM_MODEL="${MODEL}"

STATE_FILE="${ROOT_DIR}/agentic_closed_loop/state/${INSTANCE_ID}_${CLAIM_ID}.json"
mkdir -p "$(dirname "${STATE_FILE}")"

# ============================================
# CLEANUP: Remove cached state and results
# ============================================
echo ""
echo "Cleaning up cached state and results..."
if [[ -f "${STATE_FILE}" ]]; then
  echo "  - Removing state file: ${STATE_FILE}"
  rm -f "${STATE_FILE}"
fi

# Clean up generated test file
INSTANCE_SLUG=$(echo "${INSTANCE_ID}" | sed 's/[^a-zA-Z0-9_-]/_/g')
CLAIM_SLUG=$(echo "${CLAIM_ID}" | sed 's/[^a-zA-Z0-9_-]/_/g')
TEST_FILE="${ROOT_DIR}/claim_test_generation/tests_out/${INSTANCE_ID}/${INSTANCE_SLUG}__test_claim_${CLAIM_SLUG}.py"
if [[ -f "${TEST_FILE}" ]]; then
  echo "  - Removing old test file: ${TEST_FILE}"
  rm -f "${TEST_FILE}"
fi

# Clean up cached verification results
VERIFY_CACHE="${ROOT_DIR}/claim_test_verification/verification_out/${INSTANCE_ID}"
if [[ -d "${VERIFY_CACHE}" ]]; then
  echo "  - Removing cached verification results: ${VERIFY_CACHE}"
  rm -rf "${VERIFY_CACHE}"
fi
echo "✓ Cleanup complete"

COMMON_ARGS=(
  --instance_id "${INSTANCE_ID}"
  --claim_id "${CLAIM_ID}"
  --max_attempts "${MAX_ATTEMPTS}"
  --timeout_s "${TIMEOUT_S}"
  --endpoint "${ENDPOINT}"
  --repos_root "${REPOS_ROOT}"
  --state_file "${STATE_FILE}"
)
if [[ -n "${SERVER_API_KEY}" ]]; then
  COMMON_ARGS+=(--api_key "${SERVER_API_KEY}")
fi

# ============================================
# RUN ORCHESTRATOR (manages iterative loop)
# ============================================
echo ""
echo "========================================="
echo "Starting Orchestrated Iterative Loop"
echo "========================================="
set +e
PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m agentic_closed_loop.orchestrator \
  --state_file "${STATE_FILE}" \
  --instance_id "${INSTANCE_ID}" \
  --claim_id "${CLAIM_ID}" \
  --max_attempts "${MAX_ATTEMPTS}" \
  --timeout_s "${TIMEOUT_S}" \
  --repos_root "${REPOS_ROOT}" \
  --endpoint "${ENDPOINT}" \
  --model "${TESTS_MODEL}" \
  --claims-model "${CLAIMS_MODEL}" \
  --tests-model "${TESTS_MODEL}" \
  $(if [[ "${USE_MODEL_SUBDIRS}" == "true" ]]; then echo "--use-model-subdirs"; fi) \
  --singularity_image "${SINGULARITY_IMAGE}" \
  --conda_env verifier_llm \
  $(if [[ -n "${SERVER_API_KEY}" ]]; then echo "--api_key ${SERVER_API_KEY}"; fi)

ORCHESTRATOR_EXIT=$?
set -e

echo ""
echo "========================================="
echo "Results"
echo "========================================="
if [[ ${ORCHESTRATOR_EXIT} -eq 0 ]]; then
  echo "✓ Orchestration complete"
  cat "${STATE_FILE}" | python -m json.tool 2>/dev/null || cat "${STATE_FILE}"
else
  echo "✗ Orchestration failed with exit code ${ORCHESTRATOR_EXIT}"
fi

echo ""
echo "Stopping vLLM..."
kill ${VLLM_PID} || true
wait ${VLLM_PID} || true

echo "Done."
exit ${ORCHESTRATOR_EXIT}
