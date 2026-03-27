# Checklist TODO: Test verifies no fatal error occurs for same-name module/file
# Checklist TODO: Test uses only standard pytest fixtures
# Checklist TODO: Test avoids implementation-specific error checks
import pytest
import sys
from pylint import epylint as lint

def test_claim_c3(tmpdir, monkeypatch):
    # GIVEN: Create directory structure with module and file of same name
    module_dir = tmpdir.mkdir("a")
    module_dir.join("__init__.py").write("")
    tmpdir.join("a.py").write("import imp")  # Minimal valid content

    # Add tmpdir to Python path to make module discoverable
    monkeypatch.setitem(sys.path, 0, str(tmpdir))

    # WHEN: Run pylint on the module
    output, errors = lint.py_run("a", return_std=True)

    # THEN: No fatal errors (exit code 0 implied by successful run)
    assert errors == ""
    assert "F0010" not in output
    assert "E0611" not in output  # Check for other irrelevant errors not in claim
