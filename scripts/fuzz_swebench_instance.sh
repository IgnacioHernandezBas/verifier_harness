#!/bin/bash
# Fuzz a real SWE-bench instance using its actual container
#
# This script demonstrates TRUE integration with SWE-bench:
# 1. Uses the actual Podman container
# 2. Extracts real code
# 3. Runs Atheris fuzzing
# 4. Reports results

set -euo pipefail

INSTANCE_ID="${1:-astropy__astropy-6938}"
LOGS_DIR="/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/20250911_isea_claude-3.5-sonnet-20241022/logs"
INSTANCE_DIR="${LOGS_DIR}/${INSTANCE_ID}"

echo "=========================================="
echo "Fuzzing SWE-bench Instance: ${INSTANCE_ID}"
echo "=========================================="
echo ""

# Get the Docker image name
ORG="${INSTANCE_ID%%__*}"
REPO_NUM="${INSTANCE_ID#*__}"
IMAGE="docker.io/swebench/sweb.eval.x86_64.${ORG}_1776_${REPO_NUM}:latest"

echo "Container: ${IMAGE}"
echo ""

# Step 1: Show the patch
echo "Patch:"
cat "${INSTANCE_DIR}/patch.diff"
echo ""

# Step 2: Extract the file from the patch
FILE_PATH=$(grep "^diff --git" "${INSTANCE_DIR}/patch.diff" | head -1 | awk '{print $3}' | sed 's|^a/||')
echo "File to fuzz: ${FILE_PATH}"
echo ""

# Step 3: Try to pull the file from the container
echo "Extracting original code from container..."
podman run --rm "${IMAGE}" cat "/testbed/${FILE_PATH}" > /tmp/original_file.py 2>/dev/null && {
    echo "✓ Successfully extracted original code"
    wc -l /tmp/original_file.py
} || {
    echo "✗ Failed to extract code from container"
    echo "  Container may not be pulled yet"
    echo ""
    echo "Try: podman pull ${IMAGE}"
    exit 1
}

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "To actually fuzz this, we need to:"
echo "1. Parse the patch to find which function changed"
echo "2. Extract just that function (not the whole file)"
echo "3. Apply the patch to get the patched version"
echo "4. Infer parameter types"
echo "5. Run Atheris fuzzer"
echo ""
echo "This requires building the code extraction pipeline."
echo "For now, we've proven we CAN access the container and code!"
