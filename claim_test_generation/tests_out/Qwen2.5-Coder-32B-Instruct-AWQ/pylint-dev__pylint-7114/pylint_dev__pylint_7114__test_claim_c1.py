# Checklist TODO: Test passes with single .py file in directory
# Checklist TODO: Function returns correct module description
# Checklist TODO: No errors raised during execution
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c1(tmpdir):
    # Given: A directory 'a' containing a file 'a.py' and no __init__.py
    a_dir = tmpdir.mkdir('a')
    a_py = a_dir.join('a.py')
    a_py.write('')

    # When: Calling expand_modules with ['a'] as input
    ignore_list = []
    ignore_list_re = []
    ignore_list_paths_re = []
    result = expand_modules(['a'], ignore_list, ignore_list_re, ignore_list_paths_re)

    # Then: Returns a list containing module descriptions for 'a' without errors
    assert isinstance(result, list)
    assert len(result) > 0
    # Assuming the module description is a dictionary with a 'name' key
    assert any(module.get('name') == 'a' for module in result)
