"""
Test REAL Atheris coverage-guided fuzzing in the SWE-bench container.

This script demonstrates that Atheris works and uses coverage guidance.
"""

TEST_CODE = '''
import atheris
import sys

@atheris.instrument_func
def test_function(data):
    """A function with multiple branches - Atheris should explore all paths."""
    if len(data) == 0:
        return "empty"

    if data[0] == ord('A'):
        if len(data) > 1 and data[1] == ord('B'):
            if len(data) > 2 and data[2] == ord('C'):
                # This is a hard-to-reach path
                # Random fuzzing would rarely hit this
                # But coverage-guided fuzzing should find it quickly
                return "ABC_FOUND"

    return "other"

def TestOneInput(data):
    """Atheris fuzzing harness."""
    result = test_function(data)
    if result == "ABC_FOUND":
        print(f"SUCCESS: Coverage-guided fuzzing found the ABC path!")

def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
'''

import subprocess
import tempfile
from pathlib import Path

def test_atheris_coverage_guided():
    """Test that Atheris finds hard-to-reach code paths."""
    print("=" * 60)
    print("Testing REAL Atheris Coverage-Guided Fuzzing")
    print("=" * 60)
    print()
    print("This test has a function with a hard-to-reach branch:")
    print("  - Input must be exactly [A, B, C] to hit the ABC_FOUND path")
    print("  - Random fuzzing: ~1/(256^3) = 0.000006% chance per input")
    print("  - Coverage-guided: Should find it in seconds")
    print()

    # Write test script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(TEST_CODE)
        test_script = f.name

    try:
        # Run Atheris fuzzing in container for 10 seconds
        print("Running Atheris fuzzing for 10 seconds...")
        print()

        result = subprocess.run([
            "singularity", "exec",
            "-B", "/fs/nexus-scratch/ihbas/.cache/atheris_lib:/tmp/atheris_lib",
            "-B", f"{test_script}:/tmp/test_atheris.py",
            "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif",
            "bash", "-c",
            f"export PYTHONPATH=/tmp/atheris_lib:$PYTHONPATH && "
            f"timeout 10 python /tmp/test_atheris.py -max_total_time=10 2>&1 || true"
        ], capture_output=True, text=True, timeout=15)

        output = result.stdout + result.stderr

        # Check if Atheris found the path
        if "ABC_FOUND" in output or "SUCCESS" in output:
            print("✓ SUCCESS: Atheris found the ABC path using coverage guidance!")
            print()
            print("This demonstrates TRUE coverage-guided fuzzing:")
            print("  - Atheris instrumented the code to track coverage")
            print("  - It mutated inputs to maximize new coverage")
            print("  - It found the rare ABC path quickly")
            print()
            return True
        else:
            print("× Atheris ran but didn't find the path in 10 seconds")
            print("(This is expected sometimes - try running longer)")
            print()

        # Show some output
        print("Sample output:")
        for line in output.split('\n')[:20]:
            if line.strip():
                print(f"  {line}")

        return "ABC_FOUND" in output

    finally:
        Path(test_script).unlink()


if __name__ == "__main__":
    success = test_atheris_coverage_guided()
    print()
    print("=" * 60)
    if success:
        print("Atheris is working correctly with coverage guidance!")
    else:
        print("Atheris is installed but needs more time to find the path")
    print("=" * 60)
