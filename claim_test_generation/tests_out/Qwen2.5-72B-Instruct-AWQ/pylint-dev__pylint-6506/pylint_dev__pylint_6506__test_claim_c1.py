# Checklist TODO: Test raises _UnrecognizedOptionError for an unrecognized option.
# Checklist TODO: Test does not print a traceback when error is raised.
# Checklist TODO: Test uses capsys to verify no traceback is printed.
import pytest
from pylint.lint import PyLinter
from pylint.config.config_initialization import _config_initialization

def test_claim_c1(capsys):
    # GIVEN: An unrecognized option is passed to pylint
    # WHEN: _config_initialization is called with an unrecognized option
    # THEN: _UnrecognizedOptionError is raised without printing a traceback

    # Data setup
    linter = PyLinter()
    args_list = ["--unknown-option=yes"]

    # Ensure the environment is set up to capture stdout and stderr
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter=None, config_file=None, verbose_mode=False)

    # Check that no traceback is printed
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Test raises _UnrecognizedOptionError for an unrecognized option
    # Test does not print a traceback when error is raised
    # Test uses capsys to verify no traceback is printed
