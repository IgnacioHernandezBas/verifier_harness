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
# Submit with: sbatch --array=1-10%3 scripts/slurm/slurm_integrated_pipeline.sh
# This runs 10 instances, max 3 parallel

echo "=========================================="
echo "Integrated Pipeline - SLURM Worker"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURM_NODELIST"
echo "Started: $(date)"
echo ""

# Dataset-specific configuration (exported via sbatch)
PIPELINE_DATASET="${PIPELINE_DATASET:-swebench}"
PIPELINE_INSTANCE_FILE="${PIPELINE_INSTANCE_FILE:-instance_ids.txt}"
PIPELINE_ENABLE_STATIC="${PIPELINE_ENABLE_STATIC:-1}"
PIPELINE_ENABLE_FUZZING="${PIPELINE_ENABLE_FUZZING:-1}"
PIPELINE_ENABLE_RULES="${PIPELINE_ENABLE_RULES:-1}"
PIPELINE_QUIX_MODE="${PIPELINE_QUIX_MODE:-regression}"
PIPELINE_QUIX_MAX_EXAMPLES="${PIPELINE_QUIX_MAX_EXAMPLES:-100}"
PIPELINE_QUIX_TIMEOUT="${PIPELINE_QUIX_TIMEOUT:-2}"

# Load conda environment
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh
conda activate verifier_env

# Resolve directories. When running under SLURM, the script is copied to a
# temporary location, so rely on SLURM_SUBMIT_DIR when available.
if [ -n "$SLURM_SUBMIT_DIR" ]; then
    REPO_ROOT="$SLURM_SUBMIT_DIR"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

cd "$REPO_ROOT" || {
    echo "ERROR: Unable to cd into repository root: $REPO_ROOT"
    exit 1
}

WORKER_SCRIPT="$REPO_ROOT/scripts/slurm/slurm_worker_integrated.py"

# Create output directories
mkdir -p logs results

# Read instance ID from file (line number = array task ID)
INSTANCE_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${PIPELINE_INSTANCE_FILE}")

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
    # python scripts/slurm/slurm_cleanup_cache.py --keep-recent 10
fi

echo ""

if [ "$PIPELINE_DATASET" = "quixbugs" ]; then
    echo "Dataset: QuixBugs"
    OUTPUT_PATH="results/quixbugs__${INSTANCE_ID}_${PIPELINE_QUIX_MODE}.json"
    CMD=(python "QuixBugs/run_patches_through_pipeline.py"
        --mode "$PIPELINE_QUIX_MODE"
        --programs "$INSTANCE_ID"
        --limit 1
        --max-examples "$PIPELINE_QUIX_MAX_EXAMPLES"
        --timeout "$PIPELINE_QUIX_TIMEOUT"
        --output "$OUTPUT_PATH"
        --per-program-dir "results/quixbugs_per_program")

    if [ "$PIPELINE_ENABLE_STATIC" -ne 1 ]; then
        CMD+=(--disable-static)
    fi
    if [ "$PIPELINE_ENABLE_RULES" -ne 1 ]; then
        CMD+=(--disable-rules)
    fi

    echo "Executing: ${CMD[*]}"
    "${CMD[@]}"
else
    echo "Dataset: SWE-bench"
    CMD=(python "$WORKER_SCRIPT"
        --instance-id "$INSTANCE_ID"
        --output "results/${INSTANCE_ID}.json"
        --verbose)

    if [ "$PIPELINE_ENABLE_STATIC" -eq 1 ]; then
        CMD+=(--enable-static)
    fi
    if [ "$PIPELINE_ENABLE_FUZZING" -eq 1 ]; then
        CMD+=(--enable-fuzzing)
    fi
    if [ "$PIPELINE_ENABLE_RULES" -eq 1 ]; then
        CMD+=(--enable-rules)
    fi

    echo "Executing: ${CMD[*]}"
    "${CMD[@]}"
fi

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
