#!/bin/bash
#SBATCH --job-name=test_hypothesis
#SBATCH --output=logs/test_hypothesis_%j.out
#SBATCH --error=logs/test_hypothesis_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --partition=cml-scavenger
#SBATCH --account=cml-scavenger
#SBATCH --qos=cml-scavenger

# ============================================
# Test Hypothesis Execution in Singularity
# ============================================
# This tests that:
# 1. Singularity image builds correctly
# 2. Fuzzing tests generate correctly
# 3. Hypothesis tests execute in container
# 4. Coverage data is collected
#
# Usage: sbatch slurm_jobs/test_hypothesis_execution.slurm

echo "=============================================="
echo "Test Hypothesis Execution in Singularity"
echo "=============================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: 4GB"
echo "Start Time: $(date)"
echo "=============================================="
echo ""

# Create directories
mkdir -p logs results

# Load Singularity module (adjust for your cluster)
# Uncomment if needed:
# module load singularity/3.8.0
# module load python/3.11

# Check if singularity is available
if ! command -v singularity &> /dev/null; then
    echo "ERROR: singularity command not found"
    echo "Try: module load singularity"
    exit 1
fi

echo "✓ Singularity version:"
singularity --version
echo ""

# Activate conda environment
source ~/.bashrc
conda activate verifier_env || {
    echo "ERROR: Could not activate verifier_env conda environment"
    echo "Available environments:"
    conda env list
    exit 1
}

echo "✓ Conda environment activated: $CONDA_DEFAULT_ENV"
echo "✓ Python version: $(python --version)"
echo ""

# Set working directory
cd /fs/nexus-scratch/ihbas/verifier_harness || {
    echo "ERROR: Could not change to project directory"
    exit 1
}

echo "✓ Working directory: $(pwd)"
echo ""

# Run the test
echo "=============================================="
echo "Running Hypothesis execution test..."
echo "=============================================="
echo ""

python test_hypothesis_execution.py

EXIT_CODE=$?

echo ""
echo "=============================================="
echo "Test Summary"
echo "=============================================="
echo "Exit code: $EXIT_CODE"
echo "End time: $(date)"

if [ $EXIT_CODE -eq 0 ]; then
    echo "Status: ✅ SUCCESS"
else
    echo "Status: ❌ FAILED"
fi

echo "=============================================="
echo ""
echo "Logs saved to:"
echo "  - logs/test_hypothesis_${SLURM_JOB_ID}.out"
echo "  - logs/test_hypothesis_${SLURM_JOB_ID}.err"
echo ""

exit $EXIT_CODE
