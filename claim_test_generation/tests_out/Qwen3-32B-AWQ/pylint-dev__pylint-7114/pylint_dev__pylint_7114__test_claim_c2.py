# Checklist TODO: Function processes directory without __init__.py
# Checklist TODO: Handles empty module files correctly
# Checklist TODO: Returns valid module list when called with proper args
import pytest
import os
from pylint.lint import expand_modules

def test_claim_c2(tmp_path):
    # Given: Create a directory with a.py and b.py, no __init__.py
    a_dir = tmp_path / "a"
    a_dir.mkdir()
    (a_dir / "a.py").touch()
    (a_dir / "b.py").touch()

    # When: Call expand_modules with the directory and required arguments
    ignore_list = []
    ignore_list_re = []
    ignore_list_paths_re = []
    result = expand_modules(str(a_dir), ignore_list, ignore_list_re, ignore_list_paths_re)

    # Then: Verify no exceptions and correct module files are included
    expected_files = {str(a_dir / "a.py"), str(a_dir / "b.py")}
    assert set(result) == expected_files
