# Checklist TODO: Test verifies absence of F0010 errors for missing __init__.py
# Checklist TODO: Test uses tmpdir to create required directory structure
# Checklist TODO: Test confirms expand_modules handles invalid directory structure gracefully
import pytest
import os
from pylint.lint import PyLinter

def test_claim_c2(tmpdir):
    # Given: Create directory 'a' with a.py but no __init__.py
    a_dir = tmpdir.mkdir("a")
    a_py = a_dir.join("a.py")
    a_py.write("pass")  # Minimal valid Python code

    # When: Initialize linter and process the directory
    linter = PyLinter()
    linter.config.persistent = 0  # Prevent config saving
    linter.check([str(a_dir)])

    # Then: No F0010 errors are present in the linter's messages
    assert "F0010" not in linter.stats["by_msg"]
