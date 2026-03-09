import pytest
from pylint.lint import expand_modules
from pylint import lint

# Given: A module with a file of the same name exists.
# When: Running pylint on the module.
# Then: No fatal error is raised.

def test_claim_c3(tmpdir, capsys):
    # Checklist: Test passes without raising a fatal error
    # Checklist: Test handles ModuleNotFoundError correctly
    # Checklist: Test handles FileNotFoundError correctly

    # Data setup: Create a module with a file of the same name
    module_name = "test_module"
    module_file = tmpdir.mkdir(module_name).join(module_name + ".py")
    module_file.write("pass")

    # Data setup: Create a test file with a valid Python module
    test_file = tmpdir.join("test_file.py")
    test_file.write("import " + module_name)

    # Data setup: Set up a valid pylint configuration
    pylint_config = tmpdir.join("pylint.cfg")
    pylint_config.write("[MASTER]\n")

    # Exercise expand_modules with module context
    try:
        expand_modules([module_file.basename], [], [], [])
    except Exception as e:
        pytest.fail(f"Fatal error raised: {e}")

    # Edge case: Module file does not exist
    try:
        expand_modules([tmpdir.join("non_existent_module").basename], [], [], [])
    except FileNotFoundError:
        pass
    else:
        pytest.fail("Expected FileNotFoundError for non-existent module file")

    # Edge case: Module file is not a valid Python file
    invalid_module_file = tmpdir.join("invalid_module.py")
    invalid_module_file.write("Invalid Python code")
    try:
        expand_modules([invalid_module_file.basename], [], [], [])
    except Exception as e:
        pass
    else:
        pytest.fail("Expected exception for invalid Python module file")

    # Edge case: Pylint configuration is invalid
    invalid_pylint_config = tmpdir.join("invalid_pylint.cfg")
    invalid_pylint_config.write("Invalid configuration")
    try:
        lint.Run(["--rcfile=" + str(invalid_pylint_config)], exit=False)
    except Exception as e:
        pass
    else:
        pytest.fail("Expected exception for invalid pylint configuration")

    # Verify no error messages were printed
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err
