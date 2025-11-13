#!/bin/bash
#SBATCH --job-name=swebench_test
#SBATCH --output=logs/test_patch_real_%j.out
#SBATCH --error=logs/test_patch_real_%j.err
#SBATCH --account=cml-scavenger
#SBATCH --partition=cml-scavenger
#SBATCH --qos=cml-scavenger
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G

# Create logs directory if needed
mkdir -p logs

# Run the Singularity-based test on pytest-dev/pytest (simple pure Python repo, actively maintained)
python verifier/dynamic_analyzers/test_real_patch_singularity.py --repo "pytest-dev/pytest" "$@"
