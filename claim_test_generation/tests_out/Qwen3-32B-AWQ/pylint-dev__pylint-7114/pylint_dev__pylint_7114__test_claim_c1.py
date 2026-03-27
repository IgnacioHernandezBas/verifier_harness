# Checklist TODO: Test shows no error for valid module structure
# Checklist TODO: Differentiates between bug and fixed behavior
# Checklist TODO: Validates correct module expansion handling
import pytest
import sys
import os
from pylint.lint import expand_modules

def test_claim_c1(tmpdir, monkeypatch):
    # Given: Module structure with same-named file and __init__.py
    module_path = tmpdir.mkdir("a")
    module_path.join("__init__.py").write("")
    module_path.join("a.py").write("import imp")

    # Add tmpdir to sys.path for module resolution
    monkeypatch.setitem(sys.modules, "a", None)  # Clear cached module
    sys.path.insert(0, str(tmpdir))

    # When: Running pylint expansion on the module
    try:
        result = expand_modules(["a"])
    finally:
        sys.path.remove(str(tmpdir))

    # Then: No error raised and module processed
    assert result is not None
    assert "F0010" not in str(result)
    assert any("a" in module for module in result)
