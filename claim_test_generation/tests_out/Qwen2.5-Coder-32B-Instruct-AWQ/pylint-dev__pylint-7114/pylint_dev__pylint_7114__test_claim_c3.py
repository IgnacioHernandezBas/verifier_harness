# Checklist TODO: Test passes without raising a fatal error.
# Checklist TODO: Output does not contain F0010 error related to file loading.
# Checklist TODO: No unexpected errors are raised during pylint execution.
import pytest
from pylint import epylint as lint

def test_claim_c3(tmpdir):
    # Given: A module with a file of the same name exists.
    module_dir = tmpdir.mkdir("a")
    module_dir.join("__init__.py").write("")
    module_dir.join("r.py").write("import a\nb = a.non_existent_name")

    # When: Running pylint on the module.
    output, errors = lint.py_run(f"{module_dir} -d all", return_std=True)

    # Then: No fatal error is raised.
    assert "F0010" not in output.getvalue()
    assert errors.getvalue() == ""
    # Output does not contain F0010 error related to file loading.
    # No unexpected errors are raised during pylint execution.
