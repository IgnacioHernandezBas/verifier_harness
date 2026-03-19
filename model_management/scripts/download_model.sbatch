#!/bin/bash
#SBATCH --job-name=Qwen/Qwen3-32B-AWQ
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger
#SBATCH --account=scavenger
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/fs/nexus-scratch/ihbas/verifier_harness/logs/download_qwen72b_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/verifier_harness/logs/download_qwen72b_%j.err

set -euo pipefail

echo "Starting Qwen/Qwen3-32B-AWQ"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: $(hostname -s)"
echo "Time: $(date)"
echo ""

# Set cache directory
export HF_HOME=/fs/cml-scratch/ihbas/cache/huggingface
export TRANSFORMERS_CACHE=/fs/cml-scratch/ihbas/cache/huggingface

# Show disk space before
echo "Disk space before download:"
df -h /fs/cml-scratch/ihbas
echo ""

# Activate conda environment
source /fs/nexus-scratch/ihbas/miniconda3/etc/profile.d/conda.sh
conda activate verifier_llm

# Create logs directory
mkdir -p /fs/nexus-scratch/ihbas/verifier_harness/logs

# Run download
echo "Starting download..."
python /fs/nexus-scratch/ihbas/verifier_harness/model_management/scripts/download_model.py

echo ""
echo "Disk space after download:"
df -h /fs/cml-scratch/ihbas
echo ""
echo "Download complete!"
echo "Time: $(date)"
