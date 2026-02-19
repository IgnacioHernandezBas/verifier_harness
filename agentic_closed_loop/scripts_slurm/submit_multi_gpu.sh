#!/bin/bash
# Helper script to submit multi-GPU agentic loop jobs with optimal configurations
#
# Usage examples:
#   ./submit_multi_gpu.sh 70b astropy__astropy-7746
#   ./submit_multi_gpu.sh 70b astropy__astropy-7746 --gpus 4
#   ./submit_multi_gpu.sh 32b pytest-dev__pytest-5413 --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
  cat <<EOF
${GREEN}Multi-GPU Agentic Loop Job Submission Helper${NC}

${BLUE}Usage:${NC}
  $(basename "$0") MODEL_SIZE INSTANCE_ID [OPTIONS]

${BLUE}Arguments:${NC}
  MODEL_SIZE      Model size configuration: 70b, 32b, or custom model name
  INSTANCE_ID     SWE-bench instance ID (e.g., astropy__astropy-7746)

${BLUE}Options:${NC}
  --gpus N                Number of GPUs (1, 2, or 4) [default: auto-select based on model]
  --claims-model MODEL    Model for claim extraction [default: Qwen/Qwen2.5-Coder-32B-Instruct-AWQ]
  --tests-model MODEL     Model for test generation [default: based on MODEL_SIZE]
  --max-attempts N        Maximum refinement attempts [default: 10]
  --claim-id ID           Claim ID to process [default: C1]
  --no-subdirs            Disable model subdirectories
  --dry-run               Show sbatch command without submitting

${BLUE}Model Size Presets:${NC}
  70b     Uses meta-llama/Meta-Llama-3.1-70B-Instruct-AWQ (2 GPUs recommended)
  32b     Uses Qwen/Qwen2.5-Coder-32B-Instruct-AWQ (1 GPU sufficient)
  7b      Uses deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct (1 GPU)
  custom  Specify full model name with --tests-model

${BLUE}Examples:${NC}
  # Run 70B model with 2 GPUs (recommended)
  $(basename "$0") 70b astropy__astropy-7746

  # Run 70B model with 4 GPUs for maximum throughput
  $(basename "$0") 70b astropy__astropy-7746 --gpus 4

  # Multimodal: Qwen for claims, Llama-70B for tests
  $(basename "$0") 70b pytest-dev__pytest-5413 --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"

  # Custom model
  $(basename "$0") 32b django__django-13321 --tests-model "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4" --gpus 2

  # Run 32B model with custom claim ID
  $(basename "$0") 32b django__django-13321 --claim-id C2

  # Dry run to see the command
  $(basename "$0") 70b astropy__astropy-7746 --dry-run

EOF
  exit 1
}

if [[ $# -lt 2 ]]; then
  usage
fi

MODEL_SIZE="$1"
INSTANCE_ID="$2"
shift 2

# Default configurations
GPU_COUNT=""
CLAIMS_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
TESTS_MODEL=""
MAX_ATTEMPTS=10
CLAIM_ID="C1"
USE_MODEL_SUBDIRS=true
DRY_RUN=false

# Parse optional arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --gpus)
      GPU_COUNT="$2"
      shift 2
      ;;
    --claims-model)
      CLAIMS_MODEL="$2"
      shift 2
      ;;
    --tests-model)
      TESTS_MODEL="$2"
      shift 2
      ;;
    --max-attempts)
      MAX_ATTEMPTS="$2"
      shift 2
      ;;
    --claim-id)
      CLAIM_ID="$2"
      shift 2
      ;;
    --no-subdirs)
      USE_MODEL_SUBDIRS=false
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo -e "${RED}Error: Unknown option $1${NC}" >&2
      usage
      ;;
  esac
done

# Set model and GPU defaults based on size
case "${MODEL_SIZE}" in
  70b)
    TESTS_MODEL="${TESTS_MODEL:-hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4}"
    GPU_COUNT="${GPU_COUNT:-2}"
    CPUS=16
    MEM=120G
    ;;
  32b)
    TESTS_MODEL="${TESTS_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct-AWQ}"
    GPU_COUNT="${GPU_COUNT:-1}"
    CPUS=8
    MEM=64G
    ;;
  7b|8b)
    TESTS_MODEL="${TESTS_MODEL:-deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct}"
    GPU_COUNT="${GPU_COUNT:-1}"
    CPUS=8
    MEM=64G
    ;;
  *)
    # Custom model name provided
    TESTS_MODEL="${TESTS_MODEL:-${MODEL_SIZE}}"
    if [[ -z "${GPU_COUNT}" ]]; then
      echo -e "${YELLOW}Warning: Unknown model size. Defaulting to 2 GPUs. Use --gpus to override.${NC}" >&2
      GPU_COUNT=2
    fi
    CPUS=16
    MEM=128G
    ;;
esac

# Adjust resources based on GPU count override
if [[ ${GPU_COUNT} -ge 4 ]]; then
  CPUS=32
  MEM=120G  # Most scavenger nodes have ~123GB max
elif [[ ${GPU_COUNT} -ge 2 ]]; then
  CPUS=16
  MEM=120G  # Most scavenger nodes have ~123GB max
fi

# Build sbatch command
SBATCH_CMD=(
  sbatch
  --export=ALL,INSTANCE_ID="${INSTANCE_ID}",CLAIM_ID="${CLAIM_ID}",CLAIMS_MODEL="${CLAIMS_MODEL}",TESTS_MODEL="${TESTS_MODEL}",MAX_ATTEMPTS="${MAX_ATTEMPTS}",USE_MODEL_SUBDIRS="${USE_MODEL_SUBDIRS}"
  --gres="gpu:rtxa6000:${GPU_COUNT}"
  --cpus-per-task="${CPUS}"
  --mem="${MEM}"
  "${SCRIPT_DIR}/run_agentic_loop_hybrid_multiple.sbatch"
)

# Display configuration
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Multi-GPU Job Submission${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Instance:${NC}      ${INSTANCE_ID}"
echo -e "${BLUE}Claim ID:${NC}      ${CLAIM_ID}"
echo -e "${BLUE}Claims Model:${NC}  ${CLAIMS_MODEL}"
echo -e "${BLUE}Tests Model:${NC}   ${TESTS_MODEL}"
echo -e "${BLUE}Max Attempts:${NC}  ${MAX_ATTEMPTS}"
echo ""
echo -e "${BLUE}Resources:${NC}"
echo -e "  GPUs:        ${GPU_COUNT} x RTX A6000"
echo -e "  CPUs:        ${CPUS}"
echo -e "  Memory:      ${MEM}"
echo ""

if [[ "${DRY_RUN}" == "true" ]]; then
  echo -e "${YELLOW}Dry run - command that would be executed:${NC}"
  echo "${SBATCH_CMD[@]}"
  exit 0
fi

# Submit job
echo -e "${GREEN}Submitting job...${NC}"
JOB_OUTPUT=$("${SBATCH_CMD[@]}")
JOB_ID=$(echo "${JOB_OUTPUT}" | grep -oP 'Submitted batch job \K\d+')

if [[ -n "${JOB_ID}" ]]; then
  echo -e "${GREEN}✓ Job submitted: ${JOB_ID}${NC}"
  echo ""
  echo -e "${BLUE}Monitor with:${NC}"
  echo "  squeue -j ${JOB_ID}"
  echo "  tail -f ${SCRIPT_DIR}/logs/agentic_multi_${JOB_ID}.out"
  echo "  tail -f ${SCRIPT_DIR}/logs/vllm_multi_${JOB_ID}.log"
else
  echo -e "${RED}✗ Job submission failed${NC}" >&2
  exit 1
fi
