# Checklist TODO: Function should not raise exceptions.
# Checklist TODO: Function should return a list of ModuleDescriptionDict.
# Checklist TODO: Test should pass with various directory contents.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c1(tmpdir):
    # Given: Create directory structure .`-- a/|-- a.py`|-- b.py` with all files empty.
    a_dir = tmpdir.mkdir('a')
    a_dir.join('a.py').write('')
    tmpdir.join('b.py').write('')

    # When: expand_modules is called with ['a'] as files_or_modules
    # Function should not raise exceptions.
    # Function should return a list of ModuleDescriptionDict.
    module_descriptions = expand_modules(['a'], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])

    # Then: No exception should be raised and the function should return a list of ModuleDescriptionDict without errors.
    assert isinstance(module_descriptions, list)
    assert len(module_descriptions) > 0

    # Edge case: Test with an empty directory.
    empty_dir = tmpdir.mkdir('empty')
    module_descriptions_empty = expand_modules([str(empty_dir)], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    assert isinstance(module_descriptions_empty, list)
    assert len(module_descriptions_empty) == 0

    # Edge case: Test with a directory containing no .py files.
    no_py_dir = tmpdir.mkdir('no_py')
    no_py_dir.join('file.txt').write('')
    module_descriptions_no_py = expand_modules([str(no_py_dir)], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    assert isinstance(module_descriptions_no_py, list)
    assert len(module_descriptions_no_py) == 0

    # Edge case: Test with a directory containing multiple .py files.
    multiple_py_dir = tmpdir.mkdir('multiple_py')
    multiple_py_dir.join('file1.py').write('')
    multiple_py_dir.join('file2.py').write('')
    module_descriptions_multiple_py = expand_modules([str(multiple_py_dir)], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    assert isinstance(module_descriptions_multiple_py, list)
    assert len(module_descriptions_multiple_py) == 2
