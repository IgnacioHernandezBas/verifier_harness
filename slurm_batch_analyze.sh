#!/bin/bash
#SBATCH --job-name=swebench_analyze
#SBATCH --output=logs/analyze_%A_%a.out
#SBATCH --error=logs/analyze_%A_%a.err
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --array=1-10%5
# Adjust array size and max parallel jobs as needed

# Set environment variables
export APPTAINER_DOCKER_USERNAME="nacheitor12"
export APPTAINER_DOCKER_PASSWORD="wN/^4Me%,!5zz_q"
export SINGULARITY_DOCKER_USERNAME="nacheitor12"
export SINGULARITY_DOCKER_PASSWORD="wN/^4Me%,!5zz_q"

# Setup paths
export WORKDIR="/fs/nexus-scratch/ihbas/verifier_harness"
export RESULTS_DIR="$WORKDIR/results/batch_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$RESULTS_DIR" "$WORKDIR/logs"

# Get instance ID
INSTANCE_FILE="$WORKDIR/instance_ids.txt"
INSTANCE_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$INSTANCE_FILE")

echo "========================================"
echo "Analyzing: $INSTANCE_ID"
echo "Job: $SLURM_JOB_ID / Task: $SLURM_ARRAY_TASK_ID"
echo "========================================"

# Run full analysis pipeline
cd "$WORKDIR"
python3 slurm_worker_analyze.py "$INSTANCE_ID" "$RESULTS_DIR"

exit $?
