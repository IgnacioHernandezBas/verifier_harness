# Checklist TODO: Test verifies function completes without raising exceptions
# Checklist TODO: Validates return value is a list of module descriptions
# Checklist TODO: Avoids implementation-specific error checking
import pytest
from pylint.lint import expand_modules

def test_claim_c2(tmpdir, monkeypatch):
    # Given: Create directory structure with a/a.py, a/b.py, and r.py
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("")
    tmpdir.join("r.py").write("from a import b")

    # When: Change working directory and call expand_modules
    monkeypatch.chdir(str(tmpdir))
    files_or_modules = ["r", "a"]

    # Then: No exception is raised and result is a list
    result = expand_modules(files_or_modules)

    # Verify result is a list of module descriptions
    assert isinstance(result, list)
    assert len(result) >= 2  # At least two modules: r and a
