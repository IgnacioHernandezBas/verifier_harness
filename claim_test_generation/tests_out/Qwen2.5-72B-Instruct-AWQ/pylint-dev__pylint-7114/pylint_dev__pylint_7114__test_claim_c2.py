# Checklist TODO: Test must verify no exceptions are raised.
# Checklist TODO: Test must confirm the return type is a list of ModuleDescriptionDict.
# Checklist TODO: Test must validate the list contains all specified modules.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c2(tmpdir, monkeypatch, capsys):
    # Given: Multiple files with the structure .`-- a/|-- a.py`|-- b.py` and `r.py` with content `from a import b`, and all files are empty.
    a_dir = tmpdir.mkdir('a')
    a_dir.join('a.py').write('')
    a_dir.join('b.py').write('')
    r_file = tmpdir.join('r.py')
    r_file.write('from a import b')

    # When: expand_modules is called with ['r', 'a'] as files_or_modules
    with monkeypatch.context() as m:
        m.chdir(tmpdir)
        result = expand_modules(['r', 'a'])

    # Then: No exception should be raised and the function should return a list of ModuleDescriptionDict without errors.
    assert isinstance(result, list), "The function should return a list."
    assert all(isinstance(item, dict) for item in result), "The list should contain ModuleDescriptionDict."
    assert len(result) == 2, "The list should contain descriptions for all specified modules."

    # Edge cases
    # Test with a non-existent module
    with pytest.raises(Exception) as exc_info:
        expand_modules(['nonexistent'])
    assert "No module named 'nonexistent'" in str(exc_info.value)

    # Test with an empty list of files_or_modules
    result = expand_modules([])
    assert isinstance(result, list), "The function should return a list."
    assert len(result) == 0, "The list should be empty for an empty input."

    # Test with a directory that does not contain any Python files
    empty_dir = tmpdir.mkdir('empty')
    result = expand_modules([str(empty_dir)])
    assert isinstance(result, list), "The function should return a list."
    assert len(result) == 0, "The list should be empty for a directory without Python files."
