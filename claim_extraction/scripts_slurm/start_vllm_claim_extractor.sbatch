#!/bin/bash
#SBATCH --job-name=claim_extractor
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:rtxa6000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/claim_extraction/scripts_slurm/logs/claims_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/claim_extraction/scripts_slurm/logs/claims_%j.err

set -euo pipefail

# ensure relative paths resolve no matter where Slurm copies the script
ROOT_DIR="${SLURM_SUBMIT_DIR:-/fs/nexus-scratch/ihbas/verifier_harness}"
cd "${ROOT_DIR}"

LOG_DIR="${ROOT_DIR}/claim_extraction/scripts_slurm/logs"
mkdir -p "${LOG_DIR}"

# --- Conda init (avoid sourcing .bashrc)
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
PORT="${CLAIM_LLM_PORT:-8000}"

is_port_free() {
  python - "$1" <<'PY'
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
  python <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

if ! is_port_free "${PORT}"; then
  if [[ -n "${CLAIM_LLM_FORCE_PORT:-}" ]]; then
    echo "ERROR: Port ${PORT} is already in use and CLAIM_LLM_FORCE_PORT is set. Exiting." >&2
    exit 1
  fi
  NEW_PORT="$(find_free_port)"
  echo "Port ${PORT} is busy. Switching to free port ${NEW_PORT}." >&2
  PORT="${NEW_PORT}"
fi

ENDPOINT="http://127.0.0.1:${PORT}/v1"
VLLM_EXTRA_ARGS=()
if [[ -n "${VLLM_API_KEY:-}" && -n "${CLAIM_LLM_API_KEY:-}" && "${VLLM_API_KEY}" != "${CLAIM_LLM_API_KEY}" ]]; then
  echo "WARNING: CLAIM_LLM_API_KEY differs from VLLM_API_KEY; using VLLM_API_KEY." >&2
fi
SERVER_API_KEY="${VLLM_API_KEY:-${CLAIM_LLM_API_KEY:-}}"
if [[ -n "${SERVER_API_KEY}" ]]; then
  export VLLM_API_KEY="${SERVER_API_KEY}"
  export CLAIM_LLM_API_KEY="${SERVER_API_KEY}"
  VLLM_EXTRA_ARGS+=(--api-key "${SERVER_API_KEY}")
fi

# Optional CUDA module (safe if not present)
module load cuda/12.6.3 2>/dev/null || true

echo "Node: $(hostname -s)"
echo "Starting vLLM server: ${MODEL}"
echo "Endpoint: ${ENDPOINT}"
if [[ -n "${SERVER_API_KEY}" ]]; then
  echo "vLLM authentication enabled (token length: ${#SERVER_API_KEY})"
fi

# Start vLLM server (unbuffered logs)
PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${PORT} \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  "${VLLM_EXTRA_ARGS[@]}" \
  > "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

# Wait until server is ready
echo "Waiting for vLLM readiness..."
CURL_ARGS=(-s -f)
if [[ -n "${SERVER_API_KEY}" ]]; then
  CURL_ARGS+=(-H "Authorization: Bearer ${SERVER_API_KEY}")
fi
for i in {1..90}; do
  if curl "${CURL_ARGS[@]}" "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "vLLM is ready."
    break
  fi
  sleep 2
done

# Hard fail if still not ready
if ! curl "${CURL_ARGS[@]}" "${ENDPOINT}/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM did not become ready in time. Tail of vLLM log:"
  tail -n 120 "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" || true
  kill ${VLLM_PID} || true
  exit 1
fi

# Export variables expected by your LLM config overrides
export CLAIM_LLM_BACKEND="vllm"
export CLAIM_LLM_ENDPOINT="${ENDPOINT}"
export CLAIM_LLM_MODEL="${MODEL}"

# Run the claim extractor (CPU-side)
echo "Running claim extraction..."
conda run -n verifier_env python -m claim_extraction.cli \
  --config claim_extraction/configs/claim_extraction.yaml \
  --input claim_extraction/instances.json \
  --out claim_extraction/claims_out/ \
  --limit 50

echo "Claim extraction finished."

# Cleanup
echo "Stopping vLLM..."
kill ${VLLM_PID} || true
wait ${VLLM_PID} || true

echo "Done."
