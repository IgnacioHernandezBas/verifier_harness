# Checklist TODO: Test setup creates a module with a file of the same name.
# Checklist TODO: Pylint runs on the module without raising a fatal error.
# Checklist TODO: Output confirms no F0010 errors are present.
import pytest
from pylint import epylint as lint

def test_claim_c3(tmpdir, monkeypatch, capsys):
    # Given: A module with a file of the same name exists.
    # Create a directory named 'a' with an __init__.py file inside.
    a_dir = tmpdir.mkdir('a')
    a_init = a_dir.join('__init__.py')
    a_init.write('')

    # Ensure the 'a' directory is in the Python path for the test.
    monkeypatch.syspath_prepend(tmpdir)

    # Create a file 'r.py' that imports from 'a'.
    r_file = tmpdir.join('r.py')
    r_file.write('import a')

    # When: Running pylint on the module.
    # Pylint runs on the module without raising a fatal error.
    lint.py_run(str(r_file), return_std=True)

    # Then: No fatal error is raised.
    # Output confirms no F0010 errors are present.
    out, err = capsys.readouterr()
    assert 'F0010' not in out
    assert 'F0010' not in err

    # Edge cases:
    # Test with an empty __init__.py file.
    a_init.write('')
    lint.py_run(str(r_file), return_std=True)
    out, err = capsys.readouterr()
    assert 'F0010' not in out
    assert 'F0010' not in err

    # Test with a non-existent module in the import statement.
    r_file.write('import b')
    lint.py_run(str(r_file), return_std=True)
    out, err = capsys.readouterr()
    assert 'F0010' not in out
    assert 'F0010' not in err

    # Test with a module that raises an exception during import.
    a_init.write('raise Exception("Test exception")')
    lint.py_run(str(r_file), return_std=True)
    out, err = capsys.readouterr()
    assert 'F0010' not in out
    assert 'F0010' not in err
