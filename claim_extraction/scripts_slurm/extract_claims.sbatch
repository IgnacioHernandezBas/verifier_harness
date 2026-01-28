#!/bin/bash
#SBATCH --job-name=extract_claims
#SBATCH --partition=cml-dpart
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/extract_%j.out
#SBATCH --error=logs/extract_%j.err

set -euo pipefail

mkdir -p logs

source ~/miniconda3/etc/profile.d/conda.sh
conda activate verifier_harness

# IMPORTANT: set this to the hostname printed by the vLLM server job log
VLLM_HOST="${VLLM_HOST:-YOUR_GPU_NODE_HOSTNAME}"
export CLAIM_LLM_ENDPOINT="http://${VLLM_HOST}:8000/v1"
export CLAIM_LLM_BACKEND="vllm"
# optionally override model name used in the request
# export CLAIM_LLM_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"

python -m claim_extraction.cli \
  --config configs/claim_extraction.yaml \
  --input instances.json \
  --out claims_out/ \
  --limit 50
