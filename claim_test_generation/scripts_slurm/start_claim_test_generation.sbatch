#!/bin/bash
#SBATCH --job-name=claim_tests
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:rtxa6000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/claim_test_generation/scripts_slurm/logs/tests_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/claim_test_generation/scripts_slurm/logs/tests_%j.err

set -euo pipefail

ROOT_DIR="${SLURM_SUBMIT_DIR:-/fs/nexus-scratch/ihbas/verifier_harness}"
cd "${ROOT_DIR}"

LOG_DIR="${ROOT_DIR}/claim_test_generation/scripts_slurm/logs"
mkdir -p "${LOG_DIR}"

source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
PORT=8000
ENDPOINT="http://127.0.0.1:${PORT}/v1"

module load cuda/12.6.3 2>/dev/null || true

echo "Node: $(hostname -s)"
echo "Starting vLLM server: ${MODEL}"
echo "Endpoint: ${ENDPOINT}"

PYTHONUNBUFFERED=1 conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${PORT} \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  > "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

echo "Waiting for vLLM readiness..."
for i in {1..90}; do
  if curl -s "${ENDPOINT}/models" >/dev/null 2>&1; then
    echo "vLLM is ready."
    break
  fi
  sleep 2
done

if ! curl -s "${ENDPOINT}/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM did not become ready in time. Tail of log:"
  tail -n 120 "${LOG_DIR}/vllm_${SLURM_JOB_ID}.log" || true
  kill ${VLLM_PID} || true
  exit 1
fi

echo "Running claim test generation..."
TEST_OUT_DIR="${ROOT_DIR}/claim_test_generation/tests_out"
mkdir -p "${TEST_OUT_DIR}"
conda run -n verifier_env python -m claim_test_generation.generate_claim_tests \
  --claims_dir claim_extraction/claims_out \
  --out_dir "${TEST_OUT_DIR}" \
  --endpoint "${ENDPOINT}"

echo "Claim test generation finished."

echo "Stopping vLLM..."
kill ${VLLM_PID} || true
wait ${VLLM_PID} || true

echo "Done."
