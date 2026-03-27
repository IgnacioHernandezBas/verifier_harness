# Checklist TODO: Test triggers __repr__ exception during collection
# Checklist TODO: Pytest handles error without crashing
# Checklist TODO: Test result correctly reports failure
import pytest
import subprocess
import sys
import os

def test_claim_c1(tmpdir):
    # GIVEN: Class with broken __getattribute__ and __repr__
    test_code = """
def test():
    class SomeClass:
        def __getattribute__(self, attr):
            raise RuntimeError("Attribute access failed")
        def __repr__(self):
            raise RuntimeError("Repr failed")
    obj = SomeClass()
    obj.some_attr  # This will trigger __getattribute__
"""
    # Write test code to a temporary file
    p = tmpdir.join("test_case.py")
    p.write(test_code)
    
    # WHEN: Run pytest on the test file
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(p)],
        capture_output=True,
        text=True
    )
    
    # THEN: Verify pytest handles the error gracefully
    # 1. Test should exit with non-zero status (error, not crash)
    assert result.returncode != 0
    
    # 2. Output should contain error message but no INTERNALERROR
    assert "INTERNALERROR" not in result.stdout + result.stderr
    assert "RuntimeError" in result.stdout + result.stderr
    
    # 3. Test result indicates failure (not skipped or unexpected pass)
    assert "FAILED" in result.stdout
