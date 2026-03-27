# Checklist TODO: Verify expand_modules processes module directories correctly
# Checklist TODO: Confirm no file-loading errors when modules have matching files
# Checklist TODO: Ensure successful execution completes without exceptions
import pytest
import os
from pylint.lint import expand_modules

def test_claim_c2(tmpdir):
    # Given: Create a directory 'a' with __init__.py
    a_dir = tmpdir.mkdir("a")
    a_dir.join("__init__.py").write("")
    
    # When: Call expand_modules with ["a"]
    expanded_modules = expand_modules(["a"])
    
    # Then: Ensure the result includes the module path without errors
    assert any(str(a_dir.join("__init__.py")) in path for path in expanded_modules)
