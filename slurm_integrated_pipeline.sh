#!/bin/bash
#SBATCH --job-name=integrated_pipeline
#SBATCH --output=logs/pipeline_%A_%a.out
#SBATCH --error=logs/pipeline_%A_%a.err
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# NOTE: No GPU needed for this pipeline (only static analysis, fuzzing, rules)

# Array job: Each task processes one instance
# Submit with: sbatch --array=1-10%3 slurm_integrated_pipeline.sh
# This runs 10 instances, max 3 parallel

echo "=========================================="
echo "Integrated Pipeline - SLURM Worker"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURM_NODELIST"
echo "Started: $(date)"
echo ""

# Load conda environment
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh
conda activate verifier_env

# Set working directory
cd /fs/nexus-scratch/ihbas/verifier_harness

# Create output directories
mkdir -p logs results

# Read instance ID from file (line number = array task ID)
INSTANCE_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" instance_ids.txt)

if [ -z "$INSTANCE_ID" ]; then
    echo "ERROR: Could not read instance ID for task $SLURM_ARRAY_TASK_ID"
    exit 1
fi

echo "Processing: $INSTANCE_ID"
echo ""

# Check available disk space before starting
AVAILABLE_GB=$(df /fs/nexus-scratch | tail -1 | awk '{print int($4/1024/1024)}')
echo "Available disk space: ${AVAILABLE_GB} GB"

if [ "$AVAILABLE_GB" -lt 5 ]; then
    echo "WARNING: Low disk space (< 5 GB). Consider running cleanup."
    # Optionally: trigger cleanup here
    # python slurm_cleanup_cache.py --keep-recent 10
fi

echo ""

# Run the integrated pipeline for this instance
python slurm_worker_integrated.py \
    --instance-id "$INSTANCE_ID" \
    --output "results/${INSTANCE_ID}.json" \
    --enable-static \
    --enable-fuzzing \
    --enable-rules \
    --verbose

EXIT_CODE=$?

echo ""
echo "Finished: $(date)"
echo "Exit code: $EXIT_CODE"

# Cleanup temporary files for this instance (keep container cached)
REPOS_TEMP_DIR="repos_temp_${SLURM_ARRAY_TASK_ID}"
if [ -d "$REPOS_TEMP_DIR" ]; then
    echo "Cleaning up: $REPOS_TEMP_DIR"
    rm -rf "$REPOS_TEMP_DIR"
fi

exit $EXIT_CODE
