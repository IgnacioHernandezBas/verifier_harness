#!/bin/bash
#SBATCH --job-name=extract_fuzz
#SBATCH --output=/fs/nexus-scratch/ihbas/slurm_logs/extract_fuzz_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/slurm_logs/extract_fuzz_%j.err
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# Test extracting code from Singularity and fuzzing on host

echo "=================================="
echo "Extract and Fuzz Test"
echo "=================================="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo ""

# First check if Singularity container exists
INSTANCE_ID="astropy__astropy-6938"
SIF_PATH="/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/${INSTANCE_ID}.sif"

if [ -f "${SIF_PATH}" ]; then
    echo "✓ Found Singularity container: ${SIF_PATH}"
else
    echo "✗ Container not found: ${SIF_PATH}"
    echo ""
    echo "Available containers:"
    ls /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache/ 2>/dev/null | head -5 || echo "  No cache directory"
    echo ""
    echo "You may need to build the container first using your Singularity runner"
fi

echo ""
echo "Running extraction test..."
python /fs/nexus-scratch/ihbas/extract_and_fuzz.py "${INSTANCE_ID}"

echo ""
echo "Finished: $(date)"
