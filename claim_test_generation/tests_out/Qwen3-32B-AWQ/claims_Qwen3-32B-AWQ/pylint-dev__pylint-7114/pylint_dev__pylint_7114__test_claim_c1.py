# Checklist TODO: Verify return value is tuple with list of modules
# Checklist TODO: Confirm module path points to actual .py file
# Checklist TODO: Ensure no false error reports in module descriptions
import pytest
import os
from pylint.lint import expand_modules

def test_claim_c1(tmpdir):
    # Given: Create directory structure with 'a/a.py' and no __init__.py
    a_dir = tmpdir.mkdir("a")
    a_py = a_dir.join("a.py")
    a_py.write("# test module\nimport imp")  # Valid Python content

    # When: Call expand_modules with ['a']
    modules, _ = expand_modules(["a"], str(tmpdir))  # Assuming expand_modules takes args and a start_dir

    # Then: Verify return value is tuple with list of modules
    assert isinstance(modules, list)
    assert len(modules) == 1

    # Check module description has correct basename and valid .py path
    module_desc = modules[0]
    assert module_desc["basename"] == "a"
    assert module_desc["basepath"].endswith("a.py")
    assert os.path.exists(module_desc["basepath"])

    # Ensure no F0010 errors in returned descriptions
    assert "F0010" not in [msg["symbol"] for msg in module_desc.get("messages", [])]
