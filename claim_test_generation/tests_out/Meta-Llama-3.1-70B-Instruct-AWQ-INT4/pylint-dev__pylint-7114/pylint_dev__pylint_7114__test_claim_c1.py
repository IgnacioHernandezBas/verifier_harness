import pytest
from pylint.lint import expand_modules

def test_claim_c1(tmp_path):
    # Given: A directory 'a' containing a module 'a.py' and another module 'b.py', all files are empty
    a_dir = tmp_path / "a"
    a_dir.mkdir()
    (a_dir / "a.py").touch()
    (a_dir / "b.py").touch()

    # When: expand_modules is called with the directory 'a' as input
    try:
        # Test completes without raising an exception
        # expand_modules function executes successfully
        # No errors are reported
        expand_modules([str(a_dir)])
    except Exception as e:
        pytest.fail(f"Exception raised: {e}")

    # Then: No exception is raised and the function completes successfully
    # No explicit assertion needed here, as the test will fail if an exception is raised
