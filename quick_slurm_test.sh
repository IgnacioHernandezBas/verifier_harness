#!/bin/bash
#SBATCH --job-name=quick_test
#SBATCH --output=logs/quick_test_%j.out
#SBATCH --error=logs/quick_test_%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --partition=main

# Quick test job - Run ONE instance directly
# Usage: sbatch quick_slurm_test.sh

echo "=========================================="
echo "🚀 Quick Test Job Started"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Time: $(date)"
echo "=========================================="
echo ""

# Setup environment
cd /home/user/verifier_harness
source /fs/nexus-projects/anaconda/etc/profile.d/conda.sh
conda activate verifier_env

# Set environment variables for the pipeline
export PIPELINE_ENABLE_STATIC="true"
export PIPELINE_ENABLE_FUZZING="true"
export PIPELINE_ENABLE_RULES="true"

# Instance to test
INSTANCE_ID="astropy__astropy-12907"

echo "📦 Instance: $INSTANCE_ID"
echo "🔧 Static Analysis: ENABLED"
echo "🔬 Fuzzing: ENABLED"
echo "📋 Rules: ENABLED"
echo ""

# Run the instance
echo "⏱️  Starting evaluation..."
python scripts/run_swebench_instance.py --instance-id "$INSTANCE_ID"

EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Job completed successfully!"
    echo "📊 Results saved to: results/${INSTANCE_ID}.json"
else
    echo "❌ Job failed with exit code: $EXIT_CODE"
fi
echo "Time: $(date)"
echo "=========================================="

exit $EXIT_CODE
