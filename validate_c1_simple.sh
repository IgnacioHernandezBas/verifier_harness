#!/bin/bash
#
# Simple Differential Validation for Claim C1
# This script runs the C1 test on C_gold and C_bug configurations
#

set -e

REPO_PATH="/fs/nexus-scratch/ihbas/verifier_harness/repos_temp_demo/astropy__astropy"
CONTAINER="/fs/nexus-scratch/ihbas/.cache/swebench_singularity/astropy/astropy__astropy-7746.sif"
CLAIM_TESTS="claim_tests/astropy__astropy-7746"

echo "================================================================================"
echo "🔬 Differential Validation: astropy__astropy-7746 - Claim C1"
echo "================================================================================"

# Change to repo directory
cd "$REPO_PATH"

# Check if patch is applied
echo ""
echo "📋 Checking current state..."
if git diff --quiet astropy/wcs/wcs.py; then
    echo "⚠️  No modifications detected - patch may not be applied"
    PATCH_APPLIED=false
else
    echo "✅ Modifications detected in astropy/wcs/wcs.py (patch appears to be applied)"
    PATCH_APPLIED=true
fi

# Save the patch for later reapplication
git diff > /tmp/astropy-7746-patch.diff
echo "💾 Saved current diff to /tmp/astropy-7746-patch.diff"

# ============================================================================
# PHASE 1: C_gold (WITH patch) - Test should PASS
# ============================================================================
echo ""
echo "================================================================================"
echo "✨ PHASE 1: C_gold (base_commit + gold patch)"
echo "================================================================================"

if [ "$PATCH_APPLIED" = true ]; then
    echo "✅ Patch is already applied"
else
    echo "❌ Patch not applied - applying it now..."
    git apply /tmp/astropy-7746-patch.diff
fi

echo ""
echo "🧪 Running Claim C1 test on C_gold..."
echo "Command: singularity exec --bind $REPO_PATH:/workspace $CONTAINER bash -c 'cd /workspace && python -m pytest -xvs $CLAIM_TESTS/test_C1_wcs_empty_inputs.py'"

singularity exec --bind "$REPO_PATH:/workspace" "$CONTAINER" bash -c "
    cd /workspace && \
    python -m pip install -q -e . && \
    python -m pytest -xvs $CLAIM_TESTS/test_C1_wcs_empty_inputs.py
" 2>&1 | tee /tmp/c_gold_output.txt

CGOLD_EXIT=${PIPESTATUS[0]}

echo ""
if [ $CGOLD_EXIT -eq 0 ]; then
    echo "✅ C_gold: Test PASSED (exit code: $CGOLD_EXIT)"
    CGOLD_RESULT="PASS"
else
    echo "❌ C_gold: Test FAILED (exit code: $CGOLD_EXIT)"
    CGOLD_RESULT="FAIL"
fi

# ============================================================================
# PHASE 2: C_bug (WITHOUT patch) - Test should FAIL
# ============================================================================
echo ""
echo "================================================================================"
echo "🐛 PHASE 2: C_bug (base_commit, NO patch)"
echo "================================================================================"

echo "📝 Reverting patch..."
git checkout -- astropy/wcs/wcs.py

echo "✅ Patch reverted, repo is now in buggy state"

echo ""
echo "🧪 Running Claim C1 test on C_bug..."

singularity exec --bind "$REPO_PATH:/workspace" "$CONTAINER" bash -c "
    cd /workspace && \
    python -m pip install -q -e . && \
    python -m pytest -xvs $CLAIM_TESTS/test_C1_wcs_empty_inputs.py
" 2>&1 | tee /tmp/c_bug_output.txt

CBUG_EXIT=${PIPESTATUS[0]}

echo ""
if [ $CBUG_EXIT -eq 0 ]; then
    echo "❌ C_bug: Test PASSED (exit code: $CBUG_EXIT) - UNEXPECTED!"
    CBUG_RESULT="PASS"
else
    echo "✅ C_bug: Test FAILED (exit code: $CBUG_EXIT) - Expected (bug detected)"
    CBUG_RESULT="FAIL"
fi

# ============================================================================
# PHASE 3: Restore state
# ============================================================================
echo ""
echo "================================================================================"
echo "🔄 Restoring original state..."
echo "================================================================================"

git apply /tmp/astropy-7746-patch.diff
echo "✅ Patch reapplied"

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "================================================================================"
echo "📊 VALIDATION SUMMARY"
echo "================================================================================"

echo ""
echo "Claim C1: WCS transformation methods must return empty arrays for empty input"
echo ""
echo "Results:"
echo "  1. C_bug (no patch):   $CBUG_RESULT  $([ "$CBUG_RESULT" = "FAIL" ] && echo "✅ Expected" || echo "❌ Unexpected")"
echo "  2. C_gold (with patch): $CGOLD_RESULT $([ "$CGOLD_RESULT" = "PASS" ] && echo "✅ Expected" || echo "❌ Unexpected")"
echo ""

if [ "$CBUG_RESULT" = "FAIL" ] && [ "$CGOLD_RESULT" = "PASS" ]; then
    echo "🎉 RESULT: Claim C1 is VALID"
    echo "   ✅ Test FAILS on C_bug (detects the bug)"
    echo "   ✅ Test PASSES on C_gold (fix resolves it)"
    exit 0
else
    echo "⚠️  RESULT: Claim C1 validation FAILED"
    echo "   The test does not satisfy differential execution requirements."
    exit 1
fi
