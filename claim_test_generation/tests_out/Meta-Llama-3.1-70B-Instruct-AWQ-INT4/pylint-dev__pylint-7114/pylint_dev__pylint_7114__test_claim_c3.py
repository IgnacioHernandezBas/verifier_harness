import pytest
from pylint.lint import expand_modules
import os

def test_claim_c3(tmpdir, capsys):
    # Checklist: Test passes without raising any exceptions
    # Checklist: Module resolution is not affected by expand_modules
    # Checklist: Function completes successfully with expected output

    # Data setup: Create directory 'a' with module 'a.py' and 'b.py'
    a_dir = tmpdir.mkdir("a")
    a_py = a_dir.join("a.py")
    b_py = a_dir.join("b.py")
    a_py.write("pass")
    b_py.write("pass")

    # Data setup: Create file 'r.py' that imports 'b' from 'a'
    r_py = tmpdir.join("r.py")
    r_py.write("from a import b")

    # Data setup: Set up directory 'a' and file 'r.py' as input for expand_modules
    expand_modules([str(a_dir), str(r_py)])

    # Assertions: No exception is raised
    # Assertions: Function completes successfully
    # Assertions: Module resolution is not affected
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err

    # Edge cases: Empty directory
    empty_dir = tmpdir.mkdir("empty")
    with pytest.raises(SystemExit):
        expand_modules([str(empty_dir)])

    # Edge cases: Missing module 'a.py' or 'b.py'
    missing_module_dir = tmpdir.mkdir("missing_module")
    missing_module_dir.join("a.py").write("pass")
    with pytest.raises(SystemExit):
        expand_modules([str(missing_module_dir)])

    # Edge cases: Invalid import in 'r.py'
    invalid_import_py = tmpdir.join("invalid_import.py")
    invalid_import_py.write("from invalid_module import invalid_function")
    with pytest.raises(SystemExit):
        expand_modules([str(a_dir), str(invalid_import_py)])

    # Edge cases: Non-existent directory or file
    with pytest.raises(SystemExit):
        expand_modules(["non_existent_dir"])
