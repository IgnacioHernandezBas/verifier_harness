# Checklist TODO: Test passes with a correctly structured module.
# Checklist TODO: No unexpected errors are captured in stderr.
# Checklist TODO: Pylint output does not contain F0010 or E0611 errors.
import pytest
from pylint import epylint as lint

def test_claim_c2(tmpdir, capsys):
    # Given: A module with a file of the same name exists.
    module_dir = tmpdir.mkdir("identical")
    module_dir.join("identical.py").write("import imp\n")

    # When: Running pylint on the module.
    lint.py_run(f"{module_dir} -d all", do_exit=False)

    # Then: Pylint runs successfully.
    _, errors = capsys.readouterr()
    assert "F0010" not in errors, "No F0010 error related to file parsing should be raised."
    assert "E0611" not in errors, "No E0611 error related to missing names in the module should be raised."
