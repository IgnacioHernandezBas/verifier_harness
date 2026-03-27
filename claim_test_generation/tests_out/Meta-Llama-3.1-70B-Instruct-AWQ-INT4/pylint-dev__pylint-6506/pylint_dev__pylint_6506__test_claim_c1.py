import pytest
from pylint.config import config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

# Given: An unrecognized command line option (e.g., '-Q') is provided to pylint
# When: pylint.config.config_initialization._config_initialization is called with the unrecognized option
# Then: The _UnrecognizedOptionError exception is raised but does not propagate to produce a traceback in the output

def test_claim_c1(capsys):
    # Checklist: Test raises _UnrecognizedOptionError with unrecognized option
    # Checklist: Test does not print traceback with unrecognized option
    # Checklist: Test handles valid options correctly

    # Data setup: Unrecognized command line option (e.g., '-Q')
    # Data setup: Valid args_list for _config_initialization
    linter = PyLinter()
    reporter = BaseReporter()
    args_list = ['-Q']

    # Edge case: Multiple unrecognized options
    # Edge case: No options provided
    # Edge case: Valid options provided

    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, args_list, reporter)

    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err
