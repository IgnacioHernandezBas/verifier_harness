#!/bin/bash
#SBATCH --job-name=build-atheris
#SBATCH --output=logs/build_atheris_%j.out
#SBATCH --error=logs/build_atheris_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --partition=scavenger
#SBATCH --account=scavenger

# Build Atheris Singularity container for coverage-guided fuzzing

set -e

echo "=========================================="
echo "Building Atheris Singularity Container"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Started: $(date)"

# Navigate to project root
cd /fs/nexus-scratch/ihbas/verifier_harness

# Create output directory
mkdir -p /fs/nexus-scratch/ihbas/.containers/singularity

# Build the container
DEFINITION_FILE="containers/atheris-fuzzer.def"
OUTPUT_IMAGE="/fs/nexus-scratch/ihbas/.containers/singularity/atheris-fuzzer.sif"

echo ""
echo "Definition file: $DEFINITION_FILE"
echo "Output image: $OUTPUT_IMAGE"
echo ""

# Check if singularity is available
if ! command -v singularity &> /dev/null; then
    echo "Loading singularity module..."
    module load singularity || true
fi

# Build with fakeroot (doesn't require root privileges)
echo "Building container..."
singularity build --fakeroot "$OUTPUT_IMAGE" "$DEFINITION_FILE"

echo ""
echo "Build completed: $(date)"
echo "Image location: $OUTPUT_IMAGE"
echo ""

# Verify the build
echo "Verifying Atheris installation..."
singularity exec "$OUTPUT_IMAGE" python -c "import atheris; print(f'Atheris version: {atheris.__version__}')"

echo ""
echo "Container ready for coverage-guided fuzzing!"
