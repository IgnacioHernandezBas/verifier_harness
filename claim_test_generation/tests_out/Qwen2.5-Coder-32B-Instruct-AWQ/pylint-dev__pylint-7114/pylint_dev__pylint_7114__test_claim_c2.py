# Checklist TODO: Test passes without raising F0010 exceptions
# Checklist TODO: Expand_modules correctly identifies and processes the .py file
# Checklist TODO: No unexpected exceptions are raised during the test
import pytest
from pylint.lint import expand_modules
from pylint.lint.pylinter import PyLinter
from pylint.utils import register_plugins

def test_claim_c2(tmpdir):
    # Given: A directory 'a' containing 'a.py' but no __init__.py
    dir_a = tmpdir.mkdir("a")
    dir_a.join("a.py").write("import imp")

    # Edge case: Directory name matches the .py file name
    # Edge case: Directory contains other .py files besides the one matching the directory name
    dir_a.join("b.py").write("pass")

    # Edge case: Directory is nested within another directory
    nested_dir = dir_a.mkdir("nested")
    nested_dir.join("nested.py").write("pass")

    # When: Processing the directory through expand_modules' file resolution logic
    linter = PyLinter()
    register_plugins(linter)
    linter.load_default_plugins()

    # Then: No F0010 exceptions are raised about missing __init__.py
    with pytest.raises(SystemExit) as excinfo:
        linter.check([str(dir_a)])
    
    # Check that no F0010 errors are in the stats
    assert "F0010" not in linter.stats.by_msg

    # No unexpected exceptions are raised during the test
    assert excinfo.value.code == 0
