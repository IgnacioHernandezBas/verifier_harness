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
PORT=8000
ENDPOINT="http://127.0.0.1:${PORT}/v1"

# Optional CUDA module (safe if not present)
module load cuda/12.6.3 2>/dev/null || true

echo "Node: $(hostname -s)"
echo "Starting vLLM server: ${MODEL}"
echo "Endpoint: ${ENDPOINT}"

# Start vLLM server (unbuffered logs)
PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${PORT} \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  > "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

# Wait until server is ready
echo "Waiting for vLLM readiness..."
for i in {1..90}; do
  if curl -s "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "vLLM is ready."
    break
  fi
  sleep 2
done

# Hard fail if still not ready
if ! curl -s "${ENDPOINT}/models" >/dev/null 2>&1; then
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
