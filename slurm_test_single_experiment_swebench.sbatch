#!/bin/bash
#SBATCH --job-name=swebench_test
#SBATCH --output=/fs/nexus-scratch/ihbas/slurm_logs/%x_%A.out
#SBATCH --error=/fs/nexus-scratch/ihbas/slurm_logs/%x_%A.err
#SBATCH --time=3:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger



# Configuration - passed as environment variables or defaults
EXPERIMENT_NAME="${EXPERIMENT_NAME:-}"
MAX_PARALLEL="${MAX_PARALLEL:-8}"

if [ -z "${EXPERIMENT_NAME}" ]; then
    echo "Error: EXPERIMENT_NAME not set"
    exit 1
fi

echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Experiment: ${EXPERIMENT_NAME}"
echo "Max parallel: ${MAX_PARALLEL}"
echo "Start time: $(date)"
echo ""

# Run the SWE-bench test script (FIXED VERSION)
cd /fs/nexus-scratch/ihbas
MAX_PARALLEL="${MAX_PARALLEL}" ./test_experiment_swebench_fixed.sh "${EXPERIMENT_NAME}"

EXIT_CODE=$?

echo ""
echo "End time: $(date)"
echo "Exit code: ${EXIT_CODE}"

exit ${EXIT_CODE}
