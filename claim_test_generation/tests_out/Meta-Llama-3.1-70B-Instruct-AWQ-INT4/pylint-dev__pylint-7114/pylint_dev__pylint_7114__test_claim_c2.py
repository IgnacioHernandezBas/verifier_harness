import pytest
from pylint.lint import expand_modules

def test_claim_c2(tmpdir, capsys):
    # Given: Multiple files with the structure .`-- a/|-- a.py`|-- b.py` and `r.py` with content `from a import b`, and all files are empty.
    a_dir = tmpdir.mkdir("a")
    a_dir.join("a.py").write("")
    a_dir.join("b.py").write("")
    r_py = tmpdir.join("r.py")
    r_py.write("from a import b")

    # When: expand_modules is called with ['r', 'a'] as files_or_modules
    # Checklist: Test passes without raising any exceptions
    try:
        result = expand_modules([str(r_py), str(a_dir)])
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")

    # Checklist: Returned list contains expected ModuleDescriptionDict objects
    assert len(result) > 0
    for item in result:
        assert isinstance(item, dict)

    # Checklist: Test succeeds with given inputs and directory structure
    assert result is not None

    # Edge cases
    # Checklist: Empty input list
    assert expand_modules([]) == []

    # Checklist: Input list with non-existent files
    assert expand_modules(["non_existent_file.py"]) == []

    # Checklist: Input list with non-python files
    non_python_file = tmpdir.join("non_python_file.txt")
    non_python_file.write("")
    assert expand_modules([str(non_python_file)]) == []
