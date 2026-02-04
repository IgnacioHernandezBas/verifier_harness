#!/bin/bash
#SBATCH --job-name=agentic-loop
#SBATCH --partition=cml-furongh
#SBATCH --qos=cml-high
#SBATCH --account=cml-furongh
#SBATCH --gres=gpu:rtxa6000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm/logs/agentic_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop/scripts_slurm/logs/agentic_%j.err

set -euo pipefail

ROOT_DIR="${SLURM_SUBMIT_DIR:-/fs/nexus-scratch/ihbas/verifier_harness}"
cd "${ROOT_DIR}"

LOG_DIR="${ROOT_DIR}/agentic_closed_loop/scripts_slurm/logs"
mkdir -p "${LOG_DIR}"

INSTANCE_ID="${INSTANCE_ID:-}"
CLAIM_ID="${CLAIM_ID:-C1}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-4}"
TIMEOUT_S="${TIMEOUT_S:-300}"

if [[ -z "${INSTANCE_ID}" ]]; then
  echo "ERROR: INSTANCE_ID environment variable is required. Use sbatch --export=INSTANCE_ID=..." >&2
  exit 2
fi

source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

MODEL="${CLAIM_LLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct-AWQ}"
PORT="${CLAIM_LLM_PORT:-8000}"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: Unable to locate a python interpreter. Set PYTHON_BIN in the sbatch export list." >&2
  exit 3
fi

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
if [[ -n "${VLLM_API_KEY:-}" && -n "${CLAIM_LLM_API_KEY:-}" && "${VLLM_API_KEY}" != "${CLAIM_LLM_API_KEY}" ]]; then
  echo "WARNING: CLAIM_LLM_API_KEY differs from VLLM_API_KEY; using VLLM_API_KEY." >&2
fi
SERVER_API_KEY="${VLLM_API_KEY:-${CLAIM_LLM_API_KEY:-}}"
if [[ -n "${SERVER_API_KEY}" ]]; then
  export VLLM_API_KEY="${SERVER_API_KEY}"
  export CLAIM_LLM_API_KEY="${SERVER_API_KEY}"
  VLLM_EXTRA_ARGS+=(--api-key "${SERVER_API_KEY}")
fi

module load cuda/12.6.3 2>/dev/null || true

echo "Node: $(hostname -s)"
echo "Starting vLLM with ${MODEL} on ${ENDPOINT}"

PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${PORT} \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  "${VLLM_EXTRA_ARGS[@]}" \
  > "${LOG_DIR}/vllm_agentic_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

echo "Waiting for vLLM readiness..."
CURL_ARGS=(-s -f)
if [[ -n "${SERVER_API_KEY}" ]]; then
  CURL_ARGS+=(-H "Authorization: Bearer ${SERVER_API_KEY}")
fi
for i in {1..90}; do
  if curl "${CURL_ARGS[@]}" "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "vLLM ready."
    break
  fi
  sleep 2
done

if ! curl "${CURL_ARGS[@]}" "${ENDPOINT}/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM did not start. Tail of log:"
  tail -n 120 "${LOG_DIR}/vllm_agentic_${SLURM_JOB_ID}.log" || true
  kill ${VLLM_PID} || true
  exit 1
fi

export CLAIM_LLM_BACKEND="vLLM"
export CLAIM_LLM_ENDPOINT="${ENDPOINT}"
export CLAIM_LLM_MODEL="${MODEL}"

LOOP_ARGS=(
  --instance_id "${INSTANCE_ID}"
  --claim_id "${CLAIM_ID}"
  --max_attempts "${MAX_ATTEMPTS}"
  --timeout_s "${TIMEOUT_S}"
  --endpoint "${ENDPOINT}"
)
if [[ -n "${SERVER_API_KEY}" ]]; then
  LOOP_ARGS+=(--api_key "${SERVER_API_KEY}")
fi

echo "Running agentic loop for ${INSTANCE_ID}:${CLAIM_ID}"
set +e
conda run -n verifier_env python -m agentic_closed_loop.run_agentic_loop "${LOOP_ARGS[@]}"
EXIT_CODE=$?
set -e

echo "Stopping vLLM..."
kill ${VLLM_PID} || true
wait ${VLLM_PID} || true

exit ${EXIT_CODE}
