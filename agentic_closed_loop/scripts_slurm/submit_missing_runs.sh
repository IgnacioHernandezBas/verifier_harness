#!/bin/bash
# Submit the 6 missing runs to complete the 18-instance x 4CE x 4TG matrix
# These were missed due to: (1) claim ID mismatch (C3 vs C1) for sympy-17630
#                           (2) Slurm failures for requests-2148 and pytest-5413

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

GPUS="${GPUS:-2}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-10}"

echo "Submitting 6 missing runs..."
echo ""

# 1. CE=Qwen2.5-72B, TG=Qwen2.5-72B, requests-2148 C1 (Slurm failure)
echo "[1/6] TG=Qwen2.5-72B, CE=Qwen2.5-72B, requests-2148 C1"
./submit_multi_gpu.sh 70b psf__requests-2148 \
  --claims-model "Qwen/Qwen2.5-72B-Instruct-AWQ" \
  --tests-model "Qwen/Qwen2.5-72B-Instruct-AWQ" \
  --claim-id C1 --max-attempts "${MAX_ATTEMPTS}" --gpus "${GPUS}"
sleep 1

# 2. CE=Qwen2.5-72B, TG=Qwen2.5-72B, pytest-5413 C1 (Slurm failure)
echo "[2/6] TG=Qwen2.5-72B, CE=Qwen2.5-72B, pytest-5413 C1"
./submit_multi_gpu.sh 70b pytest-dev__pytest-5413 \
  --claims-model "Qwen/Qwen2.5-72B-Instruct-AWQ" \
  --tests-model "Qwen/Qwen2.5-72B-Instruct-AWQ" \
  --claim-id C1 --max-attempts "${MAX_ATTEMPTS}" --gpus "${GPUS}"
sleep 1

# 3. CE=Qwen3-32B, TG=Qwen3-32B, sympy-17630 C3 (wrong claim ID submitted)
echo "[3/6] TG=Qwen3-32B, CE=Qwen3-32B, sympy-17630 C3"
./submit_multi_gpu.sh 70b sympy__sympy-17630 \
  --claims-model "Qwen/Qwen3-32B-AWQ" \
  --tests-model "Qwen/Qwen3-32B-AWQ" \
  --claim-id C3 --max-attempts "${MAX_ATTEMPTS}" --gpus "${GPUS}"
sleep 1

# 4. CE=Qwen3-32B, TG=Qwen2.5-72B, sympy-17630 C3 (wrong claim ID submitted)
echo "[4/6] TG=Qwen2.5-72B, CE=Qwen3-32B, sympy-17630 C3"
./submit_multi_gpu.sh 70b sympy__sympy-17630 \
  --claims-model "Qwen/Qwen3-32B-AWQ" \
  --tests-model "Qwen/Qwen2.5-72B-Instruct-AWQ" \
  --claim-id C3 --max-attempts "${MAX_ATTEMPTS}" --gpus "${GPUS}"
sleep 1

# 5. CE=Qwen3-32B, TG=Coder-32B, sympy-17630 C3 (wrong claim ID submitted)
echo "[5/6] TG=Coder-32B, CE=Qwen3-32B, sympy-17630 C3"
./submit_multi_gpu.sh 70b sympy__sympy-17630 \
  --claims-model "Qwen/Qwen3-32B-AWQ" \
  --tests-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" \
  --claim-id C3 --max-attempts "${MAX_ATTEMPTS}" --gpus "${GPUS}"
sleep 1

# 6. CE=Qwen3-32B, TG=Llama-3.1-70B, sympy-17630 C3 (wrong claim ID submitted)
echo "[6/6] TG=Llama-3.1-70B, CE=Qwen3-32B, sympy-17630 C3"
./submit_multi_gpu.sh 70b sympy__sympy-17630 \
  --claims-model "Qwen/Qwen3-32B-AWQ" \
  --tests-model "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4" \
  --claim-id C3 --max-attempts "${MAX_ATTEMPTS}" --gpus "${GPUS}"

echo ""
echo "All 6 missing runs submitted."
