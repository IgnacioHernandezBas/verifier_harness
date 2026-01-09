#!/bin/bash
#SBATCH --job-name=fuzz_swebench
#SBATCH --output=logs/fuzz_swebench_%j.out
#SBATCH --error=logs/fuzz_swebench_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --account=scavenger
#SBATCH --partition=scavenger
#SBATCH --qos=scavenger

# Fuzz a real SWE-bench instance using Atheris in its actual Podman container
#
# Usage: INSTANCE_ID=astropy__astropy-6938 sbatch scripts/slurm/fuzz_real_swebench.sh

set -euo pipefail

INSTANCE_ID="${INSTANCE_ID:-astropy__astropy-6938}"
LOGS_DIR="/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/logs"
INSTANCE_DIR="${LOGS_DIR}/${INSTANCE_ID}"

# Set TMPDIR to local scratch for Podman
export TMPDIR='/scratch0/ihbas/tmp'
mkdir -p "${TMPDIR}"

# Skip migration - it can cause crashes (following your working test_experiment_swebench_fixed.sh)
echo "Skipping Podman migration to avoid crashes..."
echo ""

echo "=========================================="
echo "Atheris Fuzzing on Real SWE-bench Instance"
echo "=========================================="
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Instance: ${INSTANCE_ID}"
echo "Started: $(date)"
echo ""

# Get container image name
ORG="${INSTANCE_ID%%__*}"
REPO_NUM="${INSTANCE_ID#*__}"
IMAGE="docker.io/swebench/sweb.eval.x86_64.${ORG}_1776_${REPO_NUM}:latest"

echo "Container: ${IMAGE}"
echo ""

# Pull container if not present
echo "Ensuring container is available..."
podman pull "${IMAGE}" 2>&1 | tail -3 || {
    echo "Using cached container"
}
echo ""

# Extract file path from patch
FILE_PATH=$(grep "^diff --git" "${INSTANCE_DIR}/patch.diff" | head -1 | awk '{print $3}' | sed 's|^a/||')
echo "Target file: ${FILE_PATH}"
echo ""

# Extract the file from container (original version)
echo "Extracting original code from container..."
ORIGINAL_FILE="/tmp/${INSTANCE_ID}_original.py"
podman run --rm "${IMAGE}" cat "/testbed/${FILE_PATH}" > "${ORIGINAL_FILE}"

if [ -f "${ORIGINAL_FILE}" ]; then
    echo "✓ Extracted original code ($(wc -l < ${ORIGINAL_FILE}) lines)"
else
    echo "✗ Failed to extract original code"
    exit 1
fi
echo ""

# Apply patch to get patched version
echo "Applying patch to get patched version..."
PATCHED_FILE="/tmp/${INSTANCE_ID}_patched.py"
cp "${ORIGINAL_FILE}" "${PATCHED_FILE}"

# Simple patch application using patch command
cd /tmp
patch -p1 "${PATCHED_FILE}" < "${INSTANCE_DIR}/patch.diff" 2>&1 || {
    echo "Patch command failed, trying alternative method..."

    # Alternative: Use podman to apply patch in container
    podman run --rm \
        -v "${INSTANCE_DIR}/patch.diff:/tmp/patch.diff:ro" \
        "${IMAGE}" \
        bash -c "cd /testbed && git apply /tmp/patch.diff && cat ${FILE_PATH}" > "${PATCHED_FILE}"
}

if [ -f "${PATCHED_FILE}" ]; then
    echo "✓ Created patched version ($(wc -l < ${PATCHED_FILE}) lines)"
else
    echo "✗ Failed to create patched version"
    exit 1
fi
echo ""

# Show the difference
echo "Patch preview:"
diff -u "${ORIGINAL_FILE}" "${PATCHED_FILE}" | head -30 || true
echo ""

# Install Atheris in container if needed
echo "Checking for Atheris in container..."
podman run --rm "${IMAGE}" python -c "import atheris; print('Atheris already present')" 2>/dev/null && {
    FUZZING_IMAGE="${IMAGE}"
} || {
    echo "Installing Atheris in container..."

    # Create temporary container and install Atheris
    CONTAINER_ID=$(podman run -d "${IMAGE}" sleep infinity)
    podman exec "${CONTAINER_ID}" pip install --user atheris

    # Commit the container with Atheris
    FUZZING_IMAGE="${IMAGE}-atheris-${SLURM_JOB_ID}"
    podman commit "${CONTAINER_ID}" "${FUZZING_IMAGE}"
    podman stop "${CONTAINER_ID}"
    podman rm "${CONTAINER_ID}"

    echo "✓ Created Atheris-enabled image: ${FUZZING_IMAGE}"
}
echo ""

echo "=========================================="
echo "Analysis Summary"
echo "=========================================="
echo ""
echo "Instance: ${INSTANCE_ID}"
echo "Original code: ${ORIGINAL_FILE}"
echo "Patched code: ${PATCHED_FILE}"
echo "Fuzzing image: ${FUZZING_IMAGE}"
echo ""
echo "Next steps to complete fuzzing:"
echo "1. Parse ${FILE_PATH} to extract changed functions"
echo "2. Identify function signatures and parameter types"
echo "3. Generate Atheris fuzzing harness"
echo "4. Run differential fuzzing in container"
echo "5. Classify divergences and report results"
echo ""
echo "For now, we've proven we can:"
echo "✓ Access SWE-bench Podman containers"
echo "✓ Extract original code"
echo "✓ Apply patches"
echo "✓ Install Atheris"
echo ""
echo "Finished: $(date)"
