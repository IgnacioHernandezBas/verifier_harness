#!/bin/bash
#SBATCH --job-name=swebench_fuzz
#SBATCH --output=/fs/nexus-scratch/ihbas/slurm_logs/%x_%A.out
#SBATCH --error=/fs/nexus-scratch/ihbas/slurm_logs/%x_%A.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# SWE-bench Fuzzing - Follows exact pattern of slurm_test_single_experiment_swebench.sbatch

# Configuration - passed as environment variables or defaults
EXPERIMENT_NAME="${EXPERIMENT_NAME:-}"
MAX_PARALLEL="${MAX_PARALLEL:-4}"

if [ -z "${EXPERIMENT_NAME}" ]; then
    echo "Error: EXPERIMENT_NAME not set"
    echo "Usage: EXPERIMENT_NAME=20250911_isea_claude-3.5-sonnet-20241022 sbatch slurm_fuzz_experiment_swebench.sbatch"
    exit 1
fi

echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Experiment: ${EXPERIMENT_NAME}"
echo "Max parallel: ${MAX_PARALLEL}"
echo "Start time: $(date)"
echo ""

# Run the SWE-bench fuzzing script
cd /fs/nexus-scratch/ihbas
MAX_PARALLEL="${MAX_PARALLEL}" ./fuzz_experiment_swebench.sh "${EXPERIMENT_NAME}"

EXIT_CODE=$?

echo ""
echo "End time: $(date)"
echo "Exit code: ${EXIT_CODE}"

exit ${EXIT_CODE}
