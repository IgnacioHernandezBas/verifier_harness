# Checklist TODO: Test passes without raising exceptions.
# Checklist TODO: Returns a list of ModuleDescriptionDict.
# Checklist TODO: List does not contain any error entries.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c2(tmpdir):
    # Given: Create directory structure: a/, a/a.py, a/b.py, r.py
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("")
    r_file = tmpdir.join("r.py")
    r_file.write("from a import b")

    # When: expand_modules is called with ['r', 'a'] as files_or_modules
    with tmpdir.as_cwd():
        module_descriptions = expand_modules(['r', 'a'])

    # Then: No exception should be raised during the execution of expand_modules.
    # Then: The function should return a list of ModuleDescriptionDict.
    assert isinstance(module_descriptions, list)
    # Then: The returned list should not contain any error entries.
    assert all('ex' not in desc for desc in module_descriptions)
