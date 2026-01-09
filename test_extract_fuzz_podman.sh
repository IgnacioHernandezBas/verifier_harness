#!/bin/bash
#SBATCH --job-name=extract_podman
#SBATCH --output=/fs/nexus-scratch/ihbas/slurm_logs/extract_podman_%j.out
#SBATCH --error=/fs/nexus-scratch/ihbas/slurm_logs/extract_podman_%j.err
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=2
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# Extract code from Podman and fuzz on host
# Uses EXACT same Podman approach as your working test_experiment_swebench_fixed.sh

export TMPDIR='/scratch0/ihbas/tmp'
mkdir -p "${TMPDIR}"

echo "=================================="
echo "Extract and Fuzz with Podman"
echo "=================================="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo ""

python /fs/nexus-scratch/ihbas/extract_and_fuzz_podman.py "astropy__astropy-6938"

echo ""
echo "Finished: $(date)"
