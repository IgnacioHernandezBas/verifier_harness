# Checklist TODO: Function completes without exceptions
# Checklist TODO: Handles directory/file name collision correctly
# Checklist TODO: Preserves module resolution for imported files
import pytest
import os
import sys
from pathlib import Path
from pylint.lint import expand_modules

def test_claim_c3(tmp_path):
    # Given: Create directory structure
    a_dir = tmp_path / "a"
    a_dir.mkdir()
    (a_dir / "a.py").write_text("pass")
    (a_dir / "b.py").write_text("pass")
    (tmp_path / "r.py").write_text("from a import b")

    # When/Then: Call expand_modules with directory 'a' and file 'r.py'
    # Ensure no exception is raised
    try:
        # Change to tmp directory to ensure correct module resolution
        os.chdir(tmp_path)
        # Call expand_modules with the directory and file
        result = expand_modules(["a", "r.py"])
        # Verify function returns without exception
        assert True
    except Exception as e:
        pytest.fail(f"expand_modules raised unexpected exception: {e!r}")
