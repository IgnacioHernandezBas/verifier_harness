#!/bin/bash
#SBATCH --job-name=verifier_app
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:rtxa6000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=streamlit/scripts_slurm/logs/app_%j.out
#SBATCH --error=streamlit/scripts_slurm/logs/app_%j.err

###############################################################################
# Unified Verifier App Launcher
#
# Starts vLLM + Streamlit on the SAME GPU node.
#
# Usage:
#   cd /fs/nexus-scratch/ihbas/verifier_harness
#   sbatch streamlit/scripts_slurm/launch_app.sbatch
#
# After it starts, look at the log for the SSH tunnel command, then open
# http://localhost:8501 in your browser.
###############################################################################

set -euo pipefail

ROOT_DIR="${SLURM_SUBMIT_DIR:-/fs/nexus-scratch/ihbas/verifier_harness}"
cd "${ROOT_DIR}"

LOG_DIR="${ROOT_DIR}/streamlit/scripts_slurm/logs"
mkdir -p "${LOG_DIR}"

source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

# --- Configuration (override via environment) ---
MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct-AWQ}"
VLLM_PORT="${VLLM_PORT:-8000}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"

NODE=$(hostname -s)

echo "============================================"
echo "  Unified Verifier App"
echo "============================================"
echo "Node:            ${NODE}"
echo "Job ID:          ${SLURM_JOB_ID}"
echo "vLLM model:      ${MODEL}"
echo "vLLM port:       ${VLLM_PORT}"
echo "Streamlit port:  ${STREAMLIT_PORT}"
echo "GPU:             $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
echo ""

# Optional CUDA module
module load cuda/12.6.3 2>/dev/null || true

# ---------------------------------------------------------------------------
# 1. Start vLLM server (background)
# ---------------------------------------------------------------------------
echo "[1/3] Starting vLLM server..."

PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${VLLM_PORT} \
  --gpu-memory-utilization ${GPU_MEM_UTIL} \
  --max-model-len ${MAX_MODEL_LEN} \
  > "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

# ---------------------------------------------------------------------------
# 2. Wait for vLLM to be ready
# ---------------------------------------------------------------------------
echo "[2/3] Waiting for vLLM readiness..."

ENDPOINT="http://127.0.0.1:${VLLM_PORT}/v1"
READY=false

for i in {1..120}; do
  if curl -sf "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "vLLM is ready (took ~$((i*2))s)."
    READY=true
    break
  fi
  # Check if vLLM process died
  if ! kill -0 ${VLLM_PID} 2>/dev/null; then
    echo "ERROR: vLLM process died. Last 50 lines of log:"
    tail -n 50 "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" || true
    exit 1
  fi
  sleep 2
done

if [[ "${READY}" != "true" ]]; then
  echo "ERROR: vLLM did not become ready within 240s. Log tail:"
  tail -n 100 "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" || true
  kill ${VLLM_PID} || true
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Start Streamlit (foreground)
# ---------------------------------------------------------------------------
echo "[3/3] Starting Streamlit..."
echo ""
echo "============================================"
echo "  ACCESS THE APP"
echo "============================================"
echo ""
echo "  From your LOCAL machine, run:"
echo ""
echo "    ssh -N -L ${STREAMLIT_PORT}:localhost:${STREAMLIT_PORT} ${NODE}"
echo ""
echo "  Then open: http://localhost:${STREAMLIT_PORT}"
echo ""
echo "  vLLM endpoint (enter in sidebar): ${ENDPOINT}"
echo "  Model name: ${MODEL}"
echo ""
echo "============================================"
echo ""

# Export env vars so the Streamlit app picks up defaults
export CLAIM_LLM_ENDPOINT="${ENDPOINT}"
export CLAIM_LLM_MODEL="${MODEL}"

# Trap to clean up vLLM when the job ends
cleanup() {
  echo "Shutting down vLLM (PID ${VLLM_PID})..."
  kill ${VLLM_PID} 2>/dev/null || true
  wait ${VLLM_PID} 2>/dev/null || true
  echo "Cleanup complete."
}
trap cleanup EXIT INT TERM

# Run Streamlit in foreground (keeps the job alive)
conda run -n verifier_env streamlit run streamlit/app.py \
  --server.port ${STREAMLIT_PORT} \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
