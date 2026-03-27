# Checklist TODO: Test passes with valid input
# Checklist TODO: Test fails with invalid input
# Checklist TODO: Test does not check internal implementation details
import pytest
from pylint.lint import expand_modules

def test_claim_c1(tmp_path):
    # Given: A directory structure where 'a' contains 'a.py' and no __init__.py
    a_dir = tmp_path / 'a'
    a_dir.mkdir()
    (a_dir / 'a.py').touch()

    # When: Calling expand_modules with ['a'] as input
    input_paths = [str(a_dir)]

    # Then: Returns a list containing module descriptions for 'a' without errors
    # Test passes with valid input
    result = expand_modules(input_paths)
    assert len(result) > 0

    # Test does not check internal implementation details
    # Test does not raise any exceptions
    try:
        expand_modules(input_paths)
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")

    # Edge cases
    # Empty input list
    assert len(expand_modules([])) == 0

    # Input list with non-existent directory
    non_existent_dir = str(tmp_path / 'non_existent')
    assert len(expand_modules([non_existent_dir])) == 0

    # Input list with directory containing __init__.py
    init_dir = tmp_path / 'init_dir'
    init_dir.mkdir()
    (init_dir / '__init__.py').touch()
    assert len(expand_modules([str(init_dir)])) > 0
