#!/bin/bash
# Submit all instances with Llama 70B claims + Llama 70B tests
# Each instance runs as a separate job in parallel

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

CLAIMS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
TESTS_MODEL="hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
GPUS="${GPUS:-2}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-10}"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Multi-Job Submission: Llama 70B Pipeline${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Claims Model:${NC}  ${CLAIMS_MODEL}"
echo -e "${BLUE}Tests Model:${NC}   ${TESTS_MODEL}"
echo -e "${BLUE}GPUs per job:${NC}  ${GPUS}"
echo -e "${BLUE}Max Attempts:${NC}  ${MAX_ATTEMPTS}"
echo -e "${BLUE}Total Jobs:${NC}    ${#INSTANCES[@]}"
echo ""

# Track submitted jobs
JOB_IDS=()
FAILED=()

for instance in "${INSTANCES[@]}"; do
  echo -e "${BLUE}Submitting:${NC} ${instance}"

  # Submit job and capture output
  if OUTPUT=$(./submit_multi_gpu.sh 70b "${instance}" \
    --claims-model "${CLAIMS_MODEL}" \
    --tests-model "${TESTS_MODEL}" \
    --gpus "${GPUS}" \
    --max-attempts "${MAX_ATTEMPTS}" 2>&1); then

    # Extract job ID from output
    JOB_ID=$(echo "${OUTPUT}" | grep -oP 'Job submitted: \K\d+' || echo "")

    if [[ -n "${JOB_ID}" ]]; then
      JOB_IDS+=("${JOB_ID}")
      echo -e "  ${GREEN}✓ Job ${JOB_ID}${NC}"
    else
      FAILED+=("${instance}")
      echo -e "  ${YELLOW}⚠ Could not extract job ID${NC}"
    fi
  else
    FAILED+=("${instance}")
    echo -e "  ${YELLOW}⚠ Submission failed${NC}"
  fi

  # Small delay between submissions to avoid overwhelming scheduler
  sleep 1
done

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Submission Summary${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${BLUE}Total instances:${NC}  ${#INSTANCES[@]}"
echo -e "${BLUE}Jobs submitted:${NC}   ${#JOB_IDS[@]}"
echo -e "${BLUE}Failed:${NC}           ${#FAILED[@]}"
echo ""

if [[ ${#JOB_IDS[@]} -gt 0 ]]; then
  echo -e "${BLUE}Job IDs:${NC}"
  printf '  %s\n' "${JOB_IDS[@]}"
  echo ""

  # Save job IDs to file for later reference
  JOB_FILE="logs/llama70b_jobs_$(date +%Y%m%d_%H%M%S).txt"
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
echo "  ls agentic_closed_loop/results/tests_Meta-Llama-3.1-70B-Instruct-AWQ-INT4/claims_Meta-Llama-3.1-70B-Instruct-AWQ-INT4/ | grep summary.json | wc -l"
echo ""

echo -e "${BLUE}Cancel all jobs (if needed):${NC}"
if [[ ${#JOB_IDS[@]} -gt 0 ]]; then
  echo "  scancel ${JOB_IDS[@]}"
fi
echo ""

echo -e "${GREEN}All jobs submitted!${NC}"
