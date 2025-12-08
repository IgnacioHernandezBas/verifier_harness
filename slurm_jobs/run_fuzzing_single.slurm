#!/bin/bash
#SBATCH --job-name=fuzzing_eval
#SBATCH --output=logs/fuzzing_%j.out
#SBATCH --error=logs/fuzzing_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH --partition=general
# NO GPU NEEDED - CPU only workload

# ============================================
# Dynamic Fuzzing Evaluation - Single Job
# ============================================
# This runs fuzzing evaluation on a predictions file
# Usage: sbatch --export=PREDICTIONS_FILE=predictions.json run_fuzzing_single.slurm

echo "=============================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: 8GB"
echo "Start Time: $(date)"
echo "=============================================="

# Create directories
mkdir -p logs results

# Load environment (adjust module names for your cluster)
# Uncomment if your cluster uses modules:
# module load singularity/3.8.0
# module load python/3.11

# Activate conda environment
source ~/.bashrc
conda activate verifier_fuzzing || conda activate verifier_env

# Set working directory
cd /fs/nexus-scratch/ihbas/verifier_harness

# Verify Singularity image exists
IMAGE_PATH="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif"
if [ ! -f "$IMAGE_PATH" ]; then
    echo "ERROR: Singularity image not found at $IMAGE_PATH"
    echo "Run: python test_singularity_build.py"
    exit 1
fi

# Check predictions file
if [ -z "$PREDICTIONS_FILE" ]; then
    PREDICTIONS_FILE="predictions.json"
fi

if [ ! -f "$PREDICTIONS_FILE" ]; then
    echo "ERROR: Predictions file not found: $PREDICTIONS_FILE"
    echo "Usage: sbatch --export=PREDICTIONS_FILE=your_file.json run_fuzzing_single.slurm"
    exit 1
fi

echo ""
echo "Processing: $PREDICTIONS_FILE"
echo "Output: results/fuzzing_results_${SLURM_JOB_ID}.json"
echo ""

# Run evaluation
python scripts/eval_cli.py \
    --predictions "$PREDICTIONS_FILE" \
    --dataset "princeton-nlp/SWE-bench_Verified" \
    --output "results/fuzzing_results_${SLURM_JOB_ID}.json" \
    --image "$IMAGE_PATH" \
    --timeout 180 \
    --static-threshold 0.5 \
    --coverage-threshold 0.5 \
    --verbose

EXIT_CODE=$?

echo ""
echo "=============================================="
echo "Job completed with exit code: $EXIT_CODE"
echo "End Time: $(date)"
echo "Results saved to: results/fuzzing_results_${SLURM_JOB_ID}.json"
echo "=============================================="

exit $EXIT_CODE
