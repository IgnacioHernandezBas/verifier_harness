#!/bin/bash
#SBATCH --job-name=verify_array
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/logs/array_%A_%a.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/logs/array_%A_%a.err
#SBATCH --array=0-299%50
#SBATCH --time=2:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=2
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# =============================================================================
# SLURM Array Job for Parallel SWE-bench Verification
# =============================================================================
#
# This script runs 300 instances in parallel using SLURM job arrays.
# The %50 limits concurrent jobs to 50 at a time.
#
# Usage:
#   sbatch --export=EXPERIMENT=<name> scripts/slurm_array_verification.sbatch
#
# Examples:
#   sbatch --export=EXPERIMENT=20250911_isea_claude-3.5-sonnet-20241022 scripts/slurm_array_verification.sbatch
# =============================================================================

# Configuration
EXPERIMENT="${EXPERIMENT:-20250911_isea_claude-3.5-sonnet-20241022}"
ENABLE_STATIC="${ENABLE_STATIC:-false}"
ENABLE_SWEBENCH="${ENABLE_SWEBENCH:-true}"
ENABLE_FUZZING="${ENABLE_FUZZING:-false}"
ENABLE_INVARIANCE="${ENABLE_INVARIANCE:-false}"

# Paths
HARNESS_DIR="/fs/nexus-scratch/ihbas/verifier_harness"
EXPERIMENT_DIR="${HARNESS_DIR}/../generated_patches/experiments/evaluation/lite/${EXPERIMENT}/logs"
OUTPUT_DIR="${HARNESS_DIR}/results/array_${SLURM_ARRAY_JOB_ID}"

echo "=========================================="
echo "Parallel Verification Worker"
echo "=========================================="
echo "Array Job ID: ${SLURM_ARRAY_JOB_ID}"
echo "Task ID: ${SLURM_ARRAY_TASK_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Experiment: ${EXPERIMENT}"
echo ""
echo "Analysis enabled:"
echo "  Static: ${ENABLE_STATIC}"
echo "  SWE-bench: ${ENABLE_SWEBENCH}"
echo "  Fuzzing: ${ENABLE_FUZZING}"
echo "  Invariance: ${ENABLE_INVARIANCE}"
echo ""
echo "Start time: $(date)"
echo "=========================================="

# Verify we're on a compute node with /scratch0
if [ ! -d "/scratch0" ]; then
    echo "ERROR: /scratch0 not found. This job must run on a compute node."
    exit 1
fi

# Setup scratch directory
mkdir -p /scratch0/ihbas
mkdir -p "${OUTPUT_DIR}"

# Create logs directory if needed
mkdir -p "${HARNESS_DIR}/logs"

# Get list of all instances
INSTANCES=($(ls -1 "${EXPERIMENT_DIR}"))
TOTAL_INSTANCES=${#INSTANCES[@]}

echo "Total instances found: ${TOTAL_INSTANCES}"

# Check if array task ID is valid
if [ ${SLURM_ARRAY_TASK_ID} -ge ${TOTAL_INSTANCES} ]; then
    echo "Array task ID ${SLURM_ARRAY_TASK_ID} exceeds total instances ${TOTAL_INSTANCES}"
    echo "Nothing to do."
    exit 0
fi

# Get the instance for this task
INSTANCE="${INSTANCES[${SLURM_ARRAY_TASK_ID}]}"

echo "Processing instance: ${INSTANCE}"
echo ""

# Activate conda environment
source /fs/nexus-scratch/ihbas/miniconda3/bin/activate
conda activate verifier_env

# Build command
CMD="python ${HARNESS_DIR}/scripts/run_integrated_verification.py"
CMD="${CMD} --experiment ${EXPERIMENT}"
CMD="${CMD} --instance ${INSTANCE}"
CMD="${CMD} --output ${OUTPUT_DIR}/${INSTANCE}.json"

if [ "${ENABLE_STATIC}" != "true" ]; then
    CMD="${CMD} --no-static"
fi
if [ "${ENABLE_SWEBENCH}" != "true" ]; then
    CMD="${CMD} --no-swebench"
fi
if [ "${ENABLE_FUZZING}" != "true" ]; then
    CMD="${CMD} --no-fuzzing"
fi
if [ "${ENABLE_INVARIANCE}" != "true" ]; then
    CMD="${CMD} --no-invariance"
fi

echo "Running: ${CMD}"
echo ""

# Run the verification
cd "${HARNESS_DIR}"
eval "${CMD}"
EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Task Complete"
echo "=========================================="
echo "Instance: ${INSTANCE}"
echo "Exit code: ${EXIT_CODE}"
echo "End time: $(date)"
echo "Results saved to: ${OUTPUT_DIR}/${INSTANCE}.json"
echo "=========================================="

exit ${EXIT_CODE}
