#!/bin/bash
set -euo pipefail

# SWE-bench Fuzzing Script - Follows test_experiment_swebench_fixed.sh pattern
# Adds Atheris coverage-guided fuzzing to patch verification

# Configuration
EXPERIMENT_NAME="${1:-}"
EXPERIMENT_DIR="/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/${EXPERIMENT_NAME}/logs"
OUTPUT_BASE_DIR="/scratch0/ihbas/fuzzing_results/${EXPERIMENT_NAME}"
MAX_PARALLEL="${MAX_PARALLEL:-4}"

# Set TMPDIR to local scratch for Podman (required - NFS doesn't support xattr)
export TMPDIR='/scratch0/ihbas/tmp'
mkdir -p "${TMPDIR}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "${EXPERIMENT_NAME}" ]; then
    echo "Usage: $0 <experiment_name>"
    echo "Example: $0 20250911_isea_claude-3.5-sonnet-20241022"
    exit 1
fi

echo "=================================="
echo "SWE-bench Fuzzing Verification"
echo "=================================="
echo "Experiment: ${EXPERIMENT_NAME}"
echo "Experiment DIR: ${EXPERIMENT_DIR}"
echo "Output DIR: ${OUTPUT_BASE_DIR}"
echo ""

# Check if experiment directory exists
if [ ! -d "${EXPERIMENT_DIR}" ]; then
    echo -e "${RED}Error: Experiment directory not found: ${EXPERIMENT_DIR}${NC}"
    exit 1
fi
echo "Directory check passed"

# Count instances
INSTANCE_COUNT=$(find "${EXPERIMENT_DIR}" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "Found ${INSTANCE_COUNT} instances"
echo ""

echo "=================================="
echo "Phase 1: Simple Fuzzing Demo"
echo "=================================="
echo "Testing fuzzing on realistic bug patterns..."
echo ""

# For now, demonstrate with a simple fuzzing test
# In the future, this will:
# 1. Extract changed functions from patches
# 2. Run Atheris differential fuzzing
# 3. Classify divergences
# 4. Report results

echo "Creating demo fuzzing test..."
cat > /tmp/swebench_fuzz_demo.py << 'EOF'
#!/usr/bin/env python3
"""
Demo: Atheris fuzzing on SWE-bench style bug.

This demonstrates the fuzzing approach we'll apply to real instances.
"""
import sys
from pathlib import Path
sys.path.insert(0, '/fs/nexus-scratch/ihbas/verifier_harness')

from verifier.dynamic_analyzers.atheris_fuzzer import AtherisDifferentialFuzzer

# Bug pattern: Missing return value assignment (common in SWE-bench)
ORIGINAL = '''
def process_data(data, transform):
    """Buggy: transform result is discarded."""
    if transform:
        data.replace('old', 'new')  # BUG: result not assigned!
    return data
'''

PATCHED = '''
def process_data(data, transform):
    """Fixed: properly assign transform result."""
    if transform:
        data = data.replace('old', 'new')  # FIXED
    return data
'''

print("Running Atheris fuzzing...")
fuzzer = AtherisDifferentialFuzzer(
    original_code=ORIGINAL,
    patched_code=PATCHED,
    changed_lines=[5],
    function_name='process_data',
    function_params=[
        {'name': 'data', 'type': 'str'},
        {'name': 'transform', 'type': 'bool'},
    ],
    issue_description='Transform data when requested',
    patch_description='Fix missing assignment',
)

result = fuzzer.fuzz(max_iterations=1000, timeout_seconds=10.0)

print()
print(f"Results: {result.total_inputs} inputs tested")
print(f"  Expected divergences: {result.expected_divergences}")
print(f"  Regressions: {result.regressions}")
print(f"  Verdict: {result.verdict}")

if result.expected_divergences > 0:
    print()
    print("✓ SUCCESS: Fuzzing works on SWE-bench style bugs!")
    sys.exit(0)
else:
    print()
    print("✗ No divergences found")
    sys.exit(1)
EOF

python /tmp/swebench_fuzz_demo.py

DEMO_EXIT=$?

echo ""
echo "=================================="
echo "Summary"
echo "=================================="
if [ $DEMO_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Fuzzing demo passed${NC}"
    echo ""
    echo "Next steps to complete full integration:"
    echo "1. Parse patches to extract changed functions"
    echo "2. Use Singularity (not Podman) to access instances"
    echo "3. Extract function signatures automatically"
    echo "4. Run Atheris fuzzing on all instances"
    echo "5. Integrate with existing test results"
else
    echo -e "${RED}✗ Fuzzing demo failed${NC}"
fi

echo ""
echo "Experiment: ${EXPERIMENT_NAME}"
echo "This was a proof-of-concept. Full pipeline requires:"
echo "  - Code extraction from Singularity containers"
echo "  - Function signature parsing"
echo "  - Integration with test_experiment_swebench_fixed.sh"
