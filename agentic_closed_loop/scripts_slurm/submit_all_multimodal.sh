#!/bin/bash
# Submit all instances with MULTIMODAL setup:
# - Qwen 32B for claims (faster, good quality)
# - Llama 70B for tests (high quality generation)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# All instances to process
INSTANCES=(
  "astropy__astropy-7746"
  "django__django-11964"
  "django__django-13321"
  "django__django-14997"
  "django__django-16255"
  "django__django-16408"
  "psf__requests-2148"
  "pylint-dev__pylint-5859"
  "pylint-dev__pylint-6506"
  "pylint-dev__pylint-7114"
  "pytest-dev__pytest-5413"
  "pytest-dev__pytest-7168"
  "pytest-dev__pytest-8365"
  "scikit-learn__scikit-learn-10508"
  "scikit-learn__scikit-learn-13142"
  "sympy__sympy-17630"
  "sympy__sympy-17655"
  "sympy__sympy-18057"
  "sympy__sympy-23262"
)

CLAIMS_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" #Qwen/Qwen2.5-Coder-32B-Instruct-AWQ Qwen/Qwen2.5-72B-Instruct-AWQ
TESTS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4" # hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4 Qwen/Qwen2.5-72B-Instruct-AWQ
GPUS="${GPUS:-2}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-10}"
CLAIMS_DIR="${CLAIMS_DIR:-../../claim_extraction/claims_out}"

# Function to convert model name to slug (e.g., "Qwen/Qwen2.5-32B" -> "Qwen2.5-32B")
model_to_slug() {
  local model="$1"
  echo "${model##*/}"  # Remove everything before last /
}

# Function to get number of claims for an instance
get_claim_count() {
  local instance="$1"
  local model_slug=$(model_to_slug "${CLAIMS_MODEL}")

  # Try model-specific subdirectory first
  local claims_file="${CLAIMS_DIR}/${model_slug}/${instance}.json"

  # Fall back to flat structure if model-specific file doesn't exist
  if [[ ! -f "${claims_file}" ]]; then
    claims_file="${CLAIMS_DIR}/${instance}.json"
  fi

  if [[ -f "${claims_file}" ]]; then
    jq '.claims | length' "${claims_file}" 2>/dev/null || echo "1"
  else
    echo "1"
  fi
}

# Determine which claims directory will be used
MODEL_SLUG=$(model_to_slug "${CLAIMS_MODEL}")
if [[ -d "${CLAIMS_DIR}/${MODEL_SLUG}" ]]; then
  CLAIMS_SOURCE="${CLAIMS_DIR}/${MODEL_SLUG}"
else
  CLAIMS_SOURCE="${CLAIMS_DIR}"
fi

# Count total jobs (instances * claims)
TOTAL_JOBS=0
for instance in "${INSTANCES[@]}"; do
  CLAIM_COUNT=$(get_claim_count "${instance}")
  TOTAL_JOBS=$((TOTAL_JOBS + CLAIM_COUNT))
done

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Multi-Job Submission: Multimodal Pipeline${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Claims Model:${NC}  ${CLAIMS_MODEL}"
echo -e "${BLUE}Tests Model:${NC}   ${TESTS_MODEL}"
echo -e "${BLUE}Claims Dir:${NC}    ${CLAIMS_SOURCE}"
echo -e "${BLUE}GPUs per job:${NC}  ${GPUS}"
echo -e "${BLUE}Max Attempts:${NC}  ${MAX_ATTEMPTS}"
echo -e "${BLUE}Instances:${NC}     ${#INSTANCES[@]}"
echo -e "${BLUE}Total Jobs:${NC}    ${TOTAL_JOBS}"
echo ""

# Track submitted jobs
JOB_IDS=()
FAILED=()

for instance in "${INSTANCES[@]}"; do
  # Get number of claims for this instance
  CLAIM_COUNT=$(get_claim_count "${instance}")

  echo -e "${BLUE}Processing:${NC} ${instance} (${CLAIM_COUNT} claim(s))"

  # Submit a job for each claim
  for ((claim_num=1; claim_num<=CLAIM_COUNT; claim_num++)); do
    CLAIM_ID="C${claim_num}"
    echo -e "  ${BLUE}Submitting:${NC} ${instance}:${CLAIM_ID}"

    # Submit job and capture output
    if OUTPUT=$(./submit_multi_gpu.sh 70b "${instance}" \
      --claims-model "${CLAIMS_MODEL}" \
      --tests-model "${TESTS_MODEL}" \
      --gpus "${GPUS}" \
      --max-attempts "${MAX_ATTEMPTS}" \
      --claim-id "${CLAIM_ID}" 2>&1); then

      # Extract job ID from output
      JOB_ID=$(echo "${OUTPUT}" | grep -oP 'Job submitted: \K\d+' || echo "")

      if [[ -n "${JOB_ID}" ]]; then
        JOB_IDS+=("${JOB_ID}")
        echo -e "    ${GREEN}✓ Job ${JOB_ID}${NC}"
      else
        FAILED+=("${instance}:${CLAIM_ID}")
        echo -e "    ${YELLOW}⚠ Could not extract job ID${NC}"
      fi
    else
      FAILED+=("${instance}:${CLAIM_ID}")
      echo -e "    ${YELLOW}⚠ Submission failed${NC}"
    fi

    # Small delay between submissions
    sleep 1
  done
done

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Submission Summary${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Total instances:${NC}  ${#INSTANCES[@]}"
echo -e "${BLUE}Expected jobs:${NC}    ${TOTAL_JOBS}"
echo -e "${BLUE}Jobs submitted:${NC}   ${#JOB_IDS[@]}"
echo -e "${BLUE}Failed:${NC}           ${#FAILED[@]}"
echo ""

if [[ ${#JOB_IDS[@]} -gt 0 ]]; then
  echo -e "${BLUE}Job IDs:${NC}"
  printf '  %s\n' "${JOB_IDS[@]}"
  echo ""

  # Save job IDs to file
  JOB_FILE="logs/multimodal_jobs_$(date +%Y%m%d_%H%M%S).txt"
  printf '%s\n' "${JOB_IDS[@]}" > "${JOB_FILE}"
  echo -e "${BLUE}Job IDs saved to:${NC} ${JOB_FILE}"
  echo ""
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo -e "${YELLOW}Failed instances:${NC}"
  printf '  %s\n' "${FAILED[@]}"
  echo ""
fi

echo -e "${BLUE}Monitor all jobs:${NC}"
echo "  squeue -u \$USER"
echo "  watch -n 5 'squeue -u \$USER'"
echo ""

echo -e "${BLUE}Check progress:${NC}"
echo "  # Count completed jobs"
echo "  ls agentic_closed_loop/results/tests_Meta-Llama-3.1-70B-Instruct-AWQ-INT4/claims_Qwen2.5-Coder-32B-Instruct-AWQ/ | grep summary.json | wc -l"
echo ""

echo -e "${BLUE}Cancel all jobs (if needed):${NC}"
if [[ ${#JOB_IDS[@]} -gt 0 ]]; then
  echo "  scancel ${JOB_IDS[@]}"
fi
echo ""

echo -e "${GREEN}All jobs submitted!${NC}"
