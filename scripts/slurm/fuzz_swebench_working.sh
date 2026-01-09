#!/bin/bash
#SBATCH --job-name=fuzz_swe
#SBATCH --output=logs/fuzz_swe_%j.out
#SBATCH --error=logs/fuzz_swe_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# Fuzz a real SWE-bench instance - USING YOUR WORKING PODMAN APPROACH
# This follows test_experiment_swebench_fixed.sh exactly

set -euo pipefail

INSTANCE_ID="${INSTANCE_ID:-astropy__astropy-6938}"
LOGS_DIR="/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/logs"
INSTANCE_DIR="${LOGS_DIR}/${INSTANCE_ID}"

# Set TMPDIR to local scratch for Podman (EXACTLY like your working script)
export TMPDIR='/scratch0/ihbas/tmp'
mkdir -p "${TMPDIR}"

# Skip migration (EXACTLY like your working script)
echo "Skipping Podman migration to avoid crashes..."
echo ""

echo "=========================================="
echo "Atheris Fuzzing - Using Working Podman Approach"
echo "=========================================="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Instance: ${INSTANCE_ID}"
echo "Started: $(date)"
echo ""

# Get container image name (EXACTLY like your script)
ORG="${INSTANCE_ID%%__*}"
REPO_NUM="${INSTANCE_ID#*__}"
IMAGE="docker.io/swebench/sweb.eval.x86_64.${ORG}_1776_${REPO_NUM}:latest"

echo "Container: ${IMAGE}"
echo ""

# Pull image if needed (EXACTLY like your script)
if ! podman images --format "{{.Repository}}:{{.Tag}}" | grep -Fq "${IMAGE}"; then
    echo "Pulling image..."
    podman pull "${IMAGE}" 2>&1 | tail -5
fi
echo ""

# Create scratch output directory (following your pattern)
OUTPUT_DIR="/scratch0/ihbas/fuzzing_test/${INSTANCE_ID}"
mkdir -p "${OUTPUT_DIR}"

echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Extract file path from patch
FILE_PATH=$(grep "^diff --git" "${INSTANCE_DIR}/patch.diff" | head -1 | awk '{print $3}' | sed 's|^a/||')
echo "Target file: ${FILE_PATH}"
echo ""

# Extract original code using YOUR WORKING APPROACH (with volumes and bash -c)
echo "Extracting original code..."
podman run --rm \
    -v "${OUTPUT_DIR}:/output" \
    "${IMAGE}" \
    bash -c "
        cd /testbed
        cp ${FILE_PATH} /output/original_code.py
        echo 'Original code extracted'
    " 2>&1

if [ -f "${OUTPUT_DIR}/original_code.py" ]; then
    echo "✓ Extracted original ($(wc -l < ${OUTPUT_DIR}/original_code.py) lines)"
else
    echo "✗ Failed to extract original code"
    exit 1
fi
echo ""

# Copy patch to output dir
cp "${INSTANCE_DIR}/patch.diff" "${OUTPUT_DIR}/"

# Apply patch to get patched version (using YOUR WORKING APPROACH)
echo "Creating patched version..."
podman run --rm \
    -v "${OUTPUT_DIR}:/output" \
    "${IMAGE}" \
    bash -c "
        cd /testbed
        git apply /output/patch.diff 2>&1 || echo 'Patch apply had warnings'
        cp ${FILE_PATH} /output/patched_code.py
        echo 'Patched code extracted'
    " 2>&1

if [ -f "${OUTPUT_DIR}/patched_code.py" ]; then
    echo "✓ Created patched version ($(wc -l < ${OUTPUT_DIR}/patched_code.py) lines)"
else
    echo "✗ Failed to create patched version"
    exit 1
fi
echo ""

# Show diff
echo "Diff between original and patched:"
diff -u "${OUTPUT_DIR}/original_code.py" "${OUTPUT_DIR}/patched_code.py" | head -40 || true
echo ""

echo "=========================================="
echo "SUCCESS!"
echo "=========================================="
echo ""
echo "Extracted files:"
echo "  Original: ${OUTPUT_DIR}/original_code.py"
echo "  Patched:  ${OUTPUT_DIR}/patched_code.py"
echo ""
echo "Next step: Parse these files to extract the changed function"
echo "and run Atheris fuzzing on it."
echo ""
echo "Finished: $(date)"
