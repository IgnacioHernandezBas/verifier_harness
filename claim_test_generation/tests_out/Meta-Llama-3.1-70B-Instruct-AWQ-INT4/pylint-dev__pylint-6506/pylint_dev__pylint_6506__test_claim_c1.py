import pytest
from pylint.config import config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

# Given: An unrecognized option is passed to pylint
# When: _config_initialization is called with the unrecognized option
# Then: A _UnrecognizedOptionError is raised, and a user-friendly error message is printed

def test_claim_c1(capsys):
    # Checklist: Test raises _UnrecognizedOptionError with unrecognized option
    # Checklist: Test prints user-friendly error message without traceback
    # Checklist: Test handles edge cases correctly

    # Data setup: Create a list of unrecognized options
    unrecognized_options = ["--unknown-option=yes"]

    # Data setup: Pass the list to _config_initialization
    linter = PyLinter()
    reporter = BaseReporter()
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, unrecognized_options, reporter)

    # Assertions: A user-friendly error message is printed
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err

    # Edge cases: Pass an empty list of options
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, [], reporter)

    # Edge cases: Pass a list with a single recognized option
    recognized_options = ["--help"]
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, recognized_options, reporter)

    # Edge cases: Pass a list with multiple unrecognized options
    multiple_unrecognized_options = ["--unknown-option=yes", "--another-unknown-option=no"]
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, multiple_unrecognized_options, reporter)
