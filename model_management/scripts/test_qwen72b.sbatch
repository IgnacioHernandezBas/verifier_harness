#!/bin/bash
#SBATCH --job-name=test-qwen72b
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:l40s:2
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/logs/test_qwen72b_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/logs/test_qwen72b_%j.err

set -euo pipefail

echo "========================================="
echo "Testing Qwen2.5-72B-Instruct-AWQ"
echo "========================================="
echo "Node: $(hostname -s)"
echo "Time: $(date)"
echo ""

# Set cache directory
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

module load cuda/12.6.3 2>/dev/null || true

# Activate conda
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh
conda activate verifier_llm

MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ"
PORT=8000

echo "Starting vLLM server with ${MODEL}..."
echo "Configuration: 2 GPUs, tensor-parallel-size=2"
echo ""

# Start vLLM in background
PYTHONUNBUFFERED=1 python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${PORT} \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --dtype auto \
  --trust-remote-code \
  --quantization awq_marlin \
  > /fs/nexus-scratch/ihbas/verifier_harness/logs/vllm_test_${SLURM_JOB_ID}.log 2>&1 &

VLLM_PID=$!
echo "vLLM PID: ${VLLM_PID}"

# Wait for vLLM to be ready (up to 10 minutes)
echo "Waiting for vLLM to start (72B model takes 3-5 minutes to load)..."
for i in {1..300}; do
  if curl -s -f "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "✓ vLLM ready after ~$((i * 2)) seconds"
    break
  fi
  if [[ $((i % 10)) -eq 0 ]]; then
    echo "  Still waiting... ($((i * 2))s elapsed)"
  fi
  sleep 2
done

if ! curl -s -f "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM did not start. Check logs."
  kill ${VLLM_PID} || true
  exit 1
fi

echo ""
echo "========================================="
echo "Testing with a simple query"
echo "========================================="

# Test query
curl -s http://127.0.0.1:${PORT}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-72B-Instruct-AWQ",
    "messages": [
      {"role": "user", "content": "Write a Python function to check if a number is prime. Be concise."}
    ],
    "max_tokens": 200,
    "temperature": 0.0
  }' | python -m json.tool

echo ""
echo ""
echo "========================================="
echo "Test complete!"
echo "========================================="

# Cleanup
echo "Stopping vLLM..."
kill ${VLLM_PID} || true
wait ${VLLM_PID} || true

echo "Done."
