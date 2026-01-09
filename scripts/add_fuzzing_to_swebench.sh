#!/bin/bash
# Add Atheris Fuzzing to Existing SWE-bench Evaluation
#
# This script augments your existing SWE-bench test workflow with coverage-guided fuzzing.
# It runs AFTER the normal tests to provide additional verification.
#
# Usage:
#   ./add_fuzzing_to_swebench.sh <instance_id> <patch_file> <podman_container>
#
# Example:
#   ./add_fuzzing_to_swebench.sh django__django-11001 patch.diff swebench/sweb.eval.x86_64.django_1776_django-11001

set -euo pipefail

INSTANCE_ID="${1:-}"
PATCH_FILE="${2:-}"
PODMAN_IMAGE="${3:-}"

if [ -z "${INSTANCE_ID}" ] || [ -z "${PATCH_FILE}" ] || [ -z "${PODMAN_IMAGE}" ]; then
    echo "Usage: $0 <instance_id> <patch_file> <podman_image>"
    exit 1
fi

echo "=========================================="
echo "Atheris Fuzzing for SWE-bench Instance"
echo "=========================================="
echo "Instance: ${INSTANCE_ID}"
echo "Patch: ${PATCH_FILE}"
echo "Container: ${PODMAN_IMAGE}"
echo ""

# Step 1: Install Atheris in the container (if not already present)
echo "Step 1: Ensuring Atheris is installed..."
podman run --rm "${PODMAN_IMAGE}" python -c "import atheris; print('Atheris already installed')" 2>/dev/null || {
    echo "Installing Atheris..."
    # Create a temporary container, install Atheris, commit it
    TEMP_CONTAINER=$(podman create "${PODMAN_IMAGE}" /bin/bash)
    podman start "${TEMP_CONTAINER}"
    podman exec "${TEMP_CONTAINER}" pip install --user atheris
    podman commit "${TEMP_CONTAINER}" "${PODMAN_IMAGE}-atheris"
    podman stop "${TEMP_CONTAINER}"
    podman rm "${TEMP_CONTAINER}"
    PODMAN_IMAGE="${PODMAN_IMAGE}-atheris"
    echo "Atheris installed in ${PODMAN_IMAGE}"
}

# Step 2: Extract functions to fuzz from the patch
echo ""
echo "Step 2: Analyzing patch to identify fuzzable functions..."
# TODO: Parse patch.diff to find changed functions
# For now, this is a placeholder showing what we'd do

echo "[PLACEHOLDER] Would extract:"
echo "  - Changed file paths"
echo "  - Function names"
echo "  - Line numbers"
echo "  - Parameter signatures"

# Step 3: Run fuzzing
echo ""
echo "Step 3: Running coverage-guided differential fuzzing..."
# TODO: Call the Atheris fuzzer here
echo "[PLACEHOLDER] Would run Atheris fuzzer on each changed function"

# Step 4: Generate report
echo ""
echo "Step 4: Generating fuzzing report..."
echo "[PLACEHOLDER] Would create JSON report with:"
echo "  - Divergences found"
echo "  - Regressions detected"
echo "  - Coverage metrics"
echo "  - Verdict (PASS/FAIL/WARNING)"

echo ""
echo "=========================================="
echo "Fuzzing Integration Points Identified"
echo "=========================================="
echo ""
echo "To integrate with your existing workflow, we need:"
echo ""
echo "1. Patch Parser"
echo "   - Extract changed functions from patch.diff"
echo "   - Get function signatures"
echo ""
echo "2. Code Extractor"
echo "   - Pull original code from container"
echo "   - Apply patch to get patched code"
echo ""
echo "3. Fuzzing Executor"
echo "   - Run Atheris fuzzer in Podman container"
echo "   - Collect results"
echo ""
echo "4. Result Aggregator"
echo "   - Combine with existing test results"
echo "   - Report in report.json"
echo ""
echo "Recommendation: Start with ONE instance manually, then automate"
