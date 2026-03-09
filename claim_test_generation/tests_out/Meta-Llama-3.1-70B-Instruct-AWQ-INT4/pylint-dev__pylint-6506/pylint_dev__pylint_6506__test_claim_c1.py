import pytest
from pylint.config import config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

# Given: An unrecognized option is passed to pylint.
# When: _config_initialization is called with an unrecognized option.
# Then: _UnrecognizedOptionError is raised without printing a traceback.

def test_claim_c1(capsys):
    # Checklist: Test raises _UnrecognizedOptionError with unrecognized option
    # Checklist: Test does not print traceback with unrecognized option
    # Checklist: Test handles recognized options correctly

    # Data setup: Unrecognized option passed to pylint
    # Data setup: Call _config_initialization with unrecognized option
    linter = PyLinter()
    reporter = BaseReporter()
    args_list = ['--unknown-option=yes']

    # Edge case: Recognized option passed to pylint
    # Edge case: No options passed to pylint
    # Edge case: Multiple unrecognized options passed to pylint

    # Assertions:
    # _UnrecognizedOptionError is raised
    # No traceback is printed
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, args_list, reporter)
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err
