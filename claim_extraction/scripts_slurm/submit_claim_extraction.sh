#!/bin/bash
# Helper script to submit multi-GPU claim extraction jobs
#
# Usage examples:
#   ./submit_claim_extraction.sh 70b
#   ./submit_claim_extraction.sh 70b --gpus 4
#   ./submit_claim_extraction.sh 32b --limit 5
#   ./submit_claim_extraction.sh 70b --instances my_instances.json

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
${GREEN}Multi-GPU Claim Extraction Job Submission Helper${NC}

${BLUE}Usage:${NC}
  $(basename "$0") MODEL_SIZE [OPTIONS]

${BLUE}Arguments:${NC}
  MODEL_SIZE      Model size configuration: 70b, 32b, or custom model name

${BLUE}Options:${NC}
  --gpus N                Number of GPUs (1, 2, or 4) [default: auto-select based on model]
  --model MODEL           Full model name [default: based on MODEL_SIZE]
  --config CONFIG         Config file [default: based on MODEL_SIZE]
  --instances FILE        Instances JSON file [default: claim_extraction/instances.json]
  --output-dir DIR        Output directory [default: claim_extraction/claims_out]
  --limit N               Limit number of instances to process
  --min-score N           Minimum claim score [default: from config]
  --dry-run               Show sbatch command without submitting

${BLUE}Model Size Presets:${NC}
  70b         Uses hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4 (2 GPUs recommended)
  qwen72b     Uses Qwen/Qwen2.5-72B-Instruct-AWQ (2 GPUs recommended)
  32b         Uses Qwen/Qwen2.5-Coder-32B-Instruct-AWQ (1 GPU sufficient)
  deepseek-v2 Uses casperhansen/deepseek-coder-v2-instruct-awq (2 GPUs recommended)
  custom      Specify full model name with --model

${BLUE}Examples:${NC}
  # Extract claims with Llama 70B (2 GPUs)
  $(basename "$0") 70b

  # Extract with Qwen 72B (2 GPUs, recommended)
  $(basename "$0") qwen72b

  # Extract with Llama 70B using 4 GPUs for maximum throughput
  $(basename "$0") 70b --gpus 4

  # Extract only first 5 instances with Qwen 32B
  $(basename "$0") 32b --limit 5

  # Extract with DeepSeek-V2 (2 GPUs)
  $(basename "$0") deepseek-v2

  # Use custom model
  $(basename "$0") custom --model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" --gpus 1

  # Dry run to see the command
  $(basename "$0") 70b --dry-run

EOF
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

MODEL_SIZE="$1"
shift

# Default configurations
GPU_COUNT=""
MODEL=""
CONFIG_FILE=""
INSTANCES_FILE="claim_extraction/instances.json"
OUTPUT_DIR="claim_extraction/claims_out"
LIMIT=""
MIN_SCORE=""
DRY_RUN=false

# Parse optional arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --gpus)
      GPU_COUNT="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    --instances)
      INSTANCES_FILE="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --min-score)
      MIN_SCORE="$2"
      shift 2
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
    MODEL="${MODEL:-hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4}"
    CONFIG_FILE="${CONFIG_FILE:-claim_extraction/configs/claim_extraction_llama70b.yaml}"
    GPU_COUNT="${GPU_COUNT:-2}"
    CPUS=16
    MEM=120G
    ;;
  qwen72b)
    MODEL="${MODEL:-Qwen/Qwen2.5-72B-Instruct-AWQ}"
    CONFIG_FILE="${CONFIG_FILE:-claim_extraction/configs/claim_extraction_qwen72b.yaml}"
    GPU_COUNT="${GPU_COUNT:-2}"
    CPUS=16
    MEM=120G
    ;;
  32b)
    MODEL="${MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct-AWQ}"
    CONFIG_FILE="${CONFIG_FILE:-claim_extraction/configs/claim_extraction_v2_2.yaml}"
    GPU_COUNT="${GPU_COUNT:-1}"
    CPUS=8
    MEM=64G
    ;;
  7b|8b)
    MODEL="${MODEL:-deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct}"
    CONFIG_FILE="${CONFIG_FILE:-claim_extraction/configs/claim_extraction_v2_2.yaml}"
    GPU_COUNT="${GPU_COUNT:-1}"
    CPUS=8
    MEM=64G
    ;;
  deepseek-v2)
    MODEL="${MODEL:-casperhansen/deepseek-coder-v2-instruct-awq}"
    CONFIG_FILE="${CONFIG_FILE:-claim_extraction/configs/claim_extraction_deepseek_v2.yaml}"
    GPU_COUNT="${GPU_COUNT:-2}"
    CPUS=16
    MEM=120G
    ;;
  *)
    # Custom model name provided
    MODEL="${MODEL:-${MODEL_SIZE}}"
    if [[ -z "${GPU_COUNT}" ]]; then
      echo -e "${YELLOW}Warning: Unknown model size. Defaulting to 2 GPUs. Use --gpus to override.${NC}" >&2
      GPU_COUNT=2
    fi
    if [[ -z "${CONFIG_FILE}" ]]; then
      echo -e "${RED}Error: Must specify --config for custom models${NC}" >&2
      exit 1
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

# Build sbatch export variables
EXPORT_VARS="ALL,MODEL=${MODEL},CONFIG_FILE=${CONFIG_FILE},INSTANCES_FILE=${INSTANCES_FILE},OUTPUT_DIR=${OUTPUT_DIR}"

if [[ -n "${LIMIT}" ]]; then
  EXPORT_VARS="${EXPORT_VARS},LIMIT=${LIMIT}"
fi

if [[ -n "${MIN_SCORE}" ]]; then
  EXPORT_VARS="${EXPORT_VARS},MIN_SCORE=${MIN_SCORE}"
fi

# Build sbatch command
SBATCH_CMD=(
  sbatch
  --export="${EXPORT_VARS}"
  --gres="gpu:l40s:${GPU_COUNT}"
  --cpus-per-task="${CPUS}"
  --mem="${MEM}"
  "${SCRIPT_DIR}/run_claim_extraction_multi_gpu.sbatch"
)

# Display configuration
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Claim Extraction Job Submission${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Model:${NC}         ${MODEL}"
echo -e "${BLUE}Config:${NC}        ${CONFIG_FILE}"
echo -e "${BLUE}Instances:${NC}     ${INSTANCES_FILE}"
echo -e "${BLUE}Output:${NC}        ${OUTPUT_DIR}"
if [[ -n "${LIMIT}" ]]; then
  echo -e "${BLUE}Limit:${NC}         ${LIMIT} instances"
fi
if [[ -n "${MIN_SCORE}" ]]; then
  echo -e "${BLUE}Min Score:${NC}     ${MIN_SCORE}"
fi
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
  echo "  tail -f ${SCRIPT_DIR}/logs/claim_extract_${JOB_ID}.out"
  echo "  tail -f ${SCRIPT_DIR}/logs/vllm_claim_${JOB_ID}.log"
else
  echo -e "${RED}✗ Job submission failed${NC}" >&2
  exit 1
fi
