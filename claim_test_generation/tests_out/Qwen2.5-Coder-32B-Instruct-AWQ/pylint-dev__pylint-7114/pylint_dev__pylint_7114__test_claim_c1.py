# Checklist TODO: Test passes without exceptions.
# Checklist TODO: Returns a list of ModuleDescriptionDict.
# Checklist TODO: Handles edge cases gracefully.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c1(tmpdir):
    # Given: Create directory 'a' with files 'a.py' and 'b.py', all files are empty.
    a_dir = tmpdir.mkdir('a')
    a_dir.join('a.py').write('')
    a_dir.join('b.py').write('')

    # When: expand_modules is called with ['a'] as files_or_modules.
    try:
        module_descriptions = expand_modules(['a'], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        # Then: No exception should be raised when expand_modules is called with ['a'] as files_or_modules.
        pytest.fail(f"expand_modules raised an exception: {e}")

    # Then: The function should return a list of ModuleDescriptionDict without errors.
    assert isinstance(module_descriptions, list)

    # Edge case: Test with an empty directory 'a'.
    a_dir.remove()
    a_dir.mkdir('a')
    try:
        module_descriptions = expand_modules(['a'], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        pytest.fail(f"expand_modules raised an exception: {e}")
    assert isinstance(module_descriptions, list)

    # Edge case: Test with a non-existent directory 'a'.
    a_dir.remove()
    try:
        module_descriptions = expand_modules(['a'], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        pytest.fail(f"expand_modules raised an exception: {e}")
    assert isinstance(module_descriptions, list)

    # Edge case: Test with a directory 'a' containing no .py files.
    a_dir.join('c.txt').write('')
    try:
        module_descriptions = expand_modules(['a'], ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        pytest.fail(f"expand_modules raised an exception: {e}")
    assert isinstance(module_descriptions, list)
