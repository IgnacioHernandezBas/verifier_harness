import pytest
from pylint.lint import expand_modules

def test_claim_c2(tmp_path):
    # Given: A directory 'a' containing 'a.py' but no __init__.py
    # Create a directory 'a' containing 'a.py' but no __init__.py
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    file_a_py = dir_a / "a.py"
    file_a_py.write_text("print('Hello World')")

    # When: Processing the directory through expand_modules' file resolution logic
    # Create an instance of the parent class
    # Since expand_modules is a function, we don't need to create an instance
    # We can call it directly with the required parameters
    input_paths = [str(dir_a)]

    # Then: No F0010 exceptions are raised about missing __init__.py
    # Test passes with a directory containing a .py file but no __init__.py
    # No F0010 exceptions are raised during expand_modules execution
    # Test succeeds without checking internal implementation details
    try:
        # Call the function with the required parameters
        expand_modules(input_paths)
        # If no exception is raised, the test passes
        assert True
    except Exception as e:
        # If an exception is raised, the test fails
        assert False, f"An exception was raised: {e}"
