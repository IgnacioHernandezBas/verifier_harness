# Checklist TODO: Test passes without raising exceptions.
# Checklist TODO: Function completes successfully.
# Checklist TODO: Edge cases are handled gracefully.
import pytest
from pylint.lint.expand_modules import expand_modules

def test_claim_c1(tmpdir):
    # Given: A directory 'a' containing a module 'a.py' and another module 'b.py', all files are empty
    directory = tmpdir.mkdir("a")
    directory.join("a.py").write("")
    directory.join("b.py").write("")

    # When: expand_modules is called with the directory 'a' as input
    try:
        expand_modules(str(directory), ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        # Then: No exception is raised and the function completes successfully
        pytest.fail(f"expand_modules raised an exception: {e}")

    # Edge case: Directory 'a' contains no files
    directory.join("a.py").remove()
    directory.join("b.py").remove()
    try:
        expand_modules(str(directory), ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        pytest.fail(f"expand_modules raised an exception: {e}")

    # Edge case: Directory 'a' contains a file with a different name
    directory.join("c.py").write("")
    try:
        expand_modules(str(directory), ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        pytest.fail(f"expand_modules raised an exception: {e}")

    # Edge case: Directory 'a' is a symbolic link to another directory
    link_directory = tmpdir.mkdir("link_a")
    link_directory.join("d.py").write("")
    directory.remove(rec=1)
    directory = tmpdir.join("a")
    directory.mksymlinkto(link_directory)
    try:
        expand_modules(str(directory), ignore_list=[], ignore_list_re=[], ignore_list_paths_re=[])
    except Exception as e:
        pytest.fail(f"expand_modules raised an exception: {e}")
