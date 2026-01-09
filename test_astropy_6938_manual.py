#!/usr/bin/env python3
"""
Manual Atheris fuzzing test for astropy__astropy-6938

Bug: output_field.replace() doesn't modify in-place - result is discarded
Fix: output_field[:] = output_field.replace() - modifies in-place

This is a PERFECT test case for differential fuzzing because:
- Original: Does nothing (replace() returns new value but doesn't assign)
- Patched: Modifies the array in-place
- Fuzzing should find inputs where this matters
"""

import sys
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from verifier.dynamic_analyzers.atheris_fuzzer import AtherisDifferentialFuzzer


# Simplified version of the buggy code (original)
ORIGINAL_CODE = '''
import numpy as np

def encode_ascii(s):
    """Helper to encode ASCII."""
    if isinstance(s, bytes):
        return s
    return s.encode('ascii')

def buggy_format_conversion(output_field, format_str):
    """
    BUGGY VERSION: Replace E with D in floating point format.

    Bug: .replace() returns a new array but we don't assign it,
    so output_field is never modified!
    """
    # Replace exponent separator in floating point numbers
    if 'D' in format_str:
        output_field.replace(encode_ascii('E'), encode_ascii('D'))  # BUG: Result discarded!

    return output_field
'''

# Fixed version (patched)
PATCHED_CODE = '''
import numpy as np

def encode_ascii(s):
    """Helper to encode ASCII."""
    if isinstance(s, bytes):
        return s
    return s.encode('ascii')

def buggy_format_conversion(output_field, format_str):
    """
    FIXED VERSION: Properly modify output_field in-place.

    Fix: Use [:] = to modify the array in-place
    """
    # Replace exponent separator in floating point numbers
    if 'D' in format_str:
        output_field[:] = output_field.replace(encode_ascii('E'), encode_ascii('D'))  # FIXED!

    return output_field
'''


def test_manual_case():
    """Test that we can detect the difference manually."""
    print("=" * 80)
    print("Manual Test: Verify the bug exists")
    print("=" * 80)
    print()

    # Test case: array with 'E' that should become 'D'
    test_data = np.array([b'1.23E+05', b'4.56E-02'], dtype='|S10')

    print("Input array:", test_data)
    print()

    # Test original (buggy)
    exec(ORIGINAL_CODE, globals())
    original_result = buggy_format_conversion(test_data.copy(), 'D')
    print("Original (buggy) result:", original_result)
    print("  Expected: ['1.23E+05', '4.56E-02'] (unchanged - bug!)")
    print()

    # Test patched (fixed)
    exec(PATCHED_CODE, globals())
    patched_result = buggy_format_conversion(test_data.copy(), 'D')
    print("Patched (fixed) result:", patched_result)
    print("  Expected: ['1.23D+05', '4.56D-02'] (E->D replacement works!)")
    print()

    if not np.array_equal(original_result, patched_result):
        print("✓ SUCCESS: Fuzzing should detect this divergence!")
        return True
    else:
        print("✗ FAIL: No divergence detected (unexpected)")
        return False


def run_atheris_fuzzing():
    """Run Atheris coverage-guided fuzzing to detect the bug."""
    print()
    print("=" * 80)
    print("Atheris Coverage-Guided Fuzzing Test")
    print("=" * 80)
    print()

    # Create fuzzer
    fuzzer = AtherisDifferentialFuzzer(
        original_code=ORIGINAL_CODE,
        patched_code=PATCHED_CODE,
        changed_lines=[1264],  # Line where the fix was applied
        function_name="buggy_format_conversion",
        function_params=[
            {"name": "output_field", "type": "np.ndarray", "default": None},
            {"name": "format_str", "type": "str", "default": None},
        ],
        class_name=None,
        issue_description="Replace E with D in floating point format strings",
        patch_description="Fix: assign result of replace() back to output_field",
    )

    print("Running fuzzing for 30 seconds...")
    print("Expected: Fuzzer should find inputs where format_str contains 'D'")
    print("          and output_field contains 'E', showing the bug")
    print()

    # Run fuzzing
    result = fuzzer.fuzz(
        max_iterations=1000,
        timeout_seconds=30.0,
    )

    # Show results
    print()
    print(fuzzer.generate_report(result))

    return result


if __name__ == "__main__":
    # First, verify manually that the bug exists
    manual_success = test_manual_case()

    if not manual_success:
        print()
        print("Manual test failed - skipping fuzzing")
        sys.exit(1)

    # Now run Atheris fuzzing
    print()
    print("Press Enter to run Atheris fuzzing...")
    input()

    result = run_atheris_fuzzing()

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total inputs tested: {result.total_inputs}")
    print(f"Divergences found: {len(result.divergences)}")
    print(f"Expected fixes: {result.expected_divergences}")
    print(f"Regressions: {result.regressions}")
    print(f"Verdict: {result.verdict}")
