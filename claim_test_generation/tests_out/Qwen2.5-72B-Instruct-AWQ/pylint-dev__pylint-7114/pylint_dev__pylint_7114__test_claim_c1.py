# Checklist TODO: Test must create the required directory structure.
# Checklist TODO: Test must call expand_modules with the correct input.
# Checklist TODO: Test must verify the output matches the expected behavior.
import pytest
from pylint.lint.expand_modules import expand_modules

@pytest.fixture
def setup_directory(tmpdir, monkeypatch):
    # Create a directory 'a' in tmpdir
    a_dir = tmpdir.mkdir('a')
    # Place a file 'a.py' inside the 'a' directory
    a_py = a_dir.join('a.py')
    a_py.write('print("Hello, world!")')
    # Ensure no __init__.py file exists in the 'a' directory
    monkeypatch.chdir(tmpdir)
    return str(a_dir)

def test_claim_c1(setup_directory):
    # GIVEN: A directory structure where 'a' contains 'a.py' and no __init__.py
    # WHEN: Calling expand_modules with ['a'] as input
    result = expand_modules(['a'])
    # THEN: Returns a list containing module descriptions for 'a' without errors
    assert isinstance(result, list)
    assert len(result) > 0
    # THEN: The returned list is not empty
    assert any('a' in module for module in result)

# Edge cases
def test_empty_directory(tmpdir):
    empty_dir = tmpdir.mkdir('empty')
    result = expand_modules([str(empty_dir)])
    assert isinstance(result, list)
    assert len(result) == 0

def test_non_existent_directory():
    with pytest.raises(FileNotFoundError):
        expand_modules(['non_existent'])

def test_directory_with_only_init(tmpdir):
    init_dir = tmpdir.mkdir('init_only')
    init_py = init_dir.join('__init__.py')
    init_py.write('')
    result = expand_modules([str(init_dir)])
    assert isinstance(result, list)
    assert len(result) == 0
