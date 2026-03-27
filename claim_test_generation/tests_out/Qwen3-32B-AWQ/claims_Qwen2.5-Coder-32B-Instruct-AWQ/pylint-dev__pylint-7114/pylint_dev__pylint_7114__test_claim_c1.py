# Checklist TODO: Function runs without exception when given valid module directory
# Checklist TODO: Returns list of module descriptions for discovered files
# Checklist TODO: Correctly handles directory structure with same-name module file
import pytest
import sys
from pathlib import Path
from pylint.lint import expand_modules

def test_claim_c1(tmpdir):
    # Given: Create directory structure a/ with a.py and b.py
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("")
    
    # Set up PYTHONPATH for module resolution
    sys.path.append(str(tmpdir))
    
    # When: Call expand_modules with required parameters
    try:
        result = expand_modules(
            ["a"],
            ignore_list=[],
            ignore_list_re=None,
            ignore_list_paths_re=None
        )
    finally:
        sys.path.remove(str(tmpdir))
    
    # Then: Verify no exception and correct output
    assert isinstance(result, list)
    assert len(result) > 0
    assert all("a.py" in module["path"] for module in result)
