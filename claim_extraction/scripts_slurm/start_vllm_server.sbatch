#!/bin/bash
#SBATCH --job-name=vllm_test
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --gres=gpu:rtxa6000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=logs/vllm_test_%j.out
#SBATCH --error=logs/vllm_test_%j.err

set -euo pipefail
mkdir -p logs

source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh

MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
PORT=8000

echo "Host: $(hostname -s)"
echo "Python check:"
conda run -n verifier_llm python -c "import sys; print(sys.executable)"
conda run -n verifier_llm python -c "import vllm; print('vllm OK', vllm.__version__)"

echo "Starting vLLM..."
conda run -n verifier_llm python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --host 127.0.0.1 \
  --port ${PORT} \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192
