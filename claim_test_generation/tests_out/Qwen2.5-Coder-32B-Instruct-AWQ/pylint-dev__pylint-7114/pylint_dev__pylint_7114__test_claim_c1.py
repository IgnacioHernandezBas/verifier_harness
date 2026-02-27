# Checklist TODO: Test passes with a valid module and file.
# Checklist TODO: No errors are captured in the output.
# Checklist TODO: Test handles edge cases gracefully.
import pytest
from pylint import epylint as lint

def test_claim_c1(tmpdir, capsys):
    # Given: A module with a file of the same name exists.
    module_dir = tmpdir.mkdir("identical")
    module_dir.join("identical.py").write("import imp")

    # When: Running pylint on the module.
    lint.py_run(f"{module_dir} -d all", do_exit=False)

    # Then: No error is raised.
    _, errors = capsys.readouterr()
    assert "Unable to create directory" not in errors
    assert "Unable to create file" not in errors
    assert "PYLINTHOME is now" not in errors
    assert "but obsolescent" not in errors
