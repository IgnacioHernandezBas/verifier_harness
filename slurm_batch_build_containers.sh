#!/bin/bash
#SBATCH --job-name=swebench_build
#SBATCH --output=logs/build_%A_%a.out
#SBATCH --error=logs/build_%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --array=1-10%5
# Array 1-10 means 10 jobs, %5 means max 5 running simultaneously

# Load required modules (adjust for your HPC)
# module load singularity/1.4.4  # Uncomment if needed

# Set environment variables for Apptainer
export APPTAINER_DOCKER_USERNAME="nacheitor12"
export APPTAINER_DOCKER_PASSWORD="wN/^4Me%,!5zz_q"
export SINGULARITY_DOCKER_USERNAME="nacheitor12"
export SINGULARITY_DOCKER_PASSWORD="wN/^4Me%,!5zz_q"

# Setup paths
export WORKDIR="/fs/nexus-scratch/ihbas/verifier_harness"
export CACHE_DIR="/fs/nexus-scratch/ihbas/.cache/swebench_singularity"
export TMP_DIR="/fs/nexus-scratch/ihbas/.tmp/singularity_build"

# Create necessary directories
mkdir -p "$CACHE_DIR" "$TMP_DIR" "$WORKDIR/logs" "$WORKDIR/results"

# Get the instance ID for this array task
INSTANCE_FILE="$WORKDIR/instance_ids.txt"
INSTANCE_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$INSTANCE_FILE")

echo "========================================"
echo "SLURM Job: $SLURM_JOB_ID"
echo "Array Task: $SLURM_ARRAY_TASK_ID"
echo "Instance: $INSTANCE_ID"
echo "Node: $SLURMD_NODENAME"
echo "========================================"

# Run the build script
cd "$WORKDIR"
python3 slurm_worker_build.py "$INSTANCE_ID"

exit_code=$?
echo "Exit code: $exit_code"
exit $exit_code
