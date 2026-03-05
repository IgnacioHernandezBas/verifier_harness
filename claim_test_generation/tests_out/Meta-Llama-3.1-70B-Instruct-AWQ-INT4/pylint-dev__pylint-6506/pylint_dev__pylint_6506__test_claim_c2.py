import pytest
from pylint.lint import PyLinter
from pylint.config.config_initialization import _config_initialization
from pylint.reporters import BaseReporter

# Given: An unrecognized option is passed to pylint
# When: _config_initialization is called with the unrecognized option
# Then: The linter adds a message 'unrecognized-option' with the unrecognized option name

def test_claim_c2(capsys):
    # Checklist: Test passes with an unrecognized option
    # Checklist: Test fails with a recognized option
    # Checklist: Test handles multiple unrecognized options correctly

    # Data setup: Create a list of unrecognized options
    unrecognized_options = ["--unknown-option=yes", "--another-unknown-option=no"]

    # Data setup: Pass the list to _config_initialization
    linter = PyLinter()
    reporter = BaseReporter()
    _config_initialization(linter, unrecognized_options, reporter)

    # Assertions: The linter adds a message 'unrecognized-option' with the unrecognized option name
    captured = capsys.readouterr()
    assert "unrecognized option" in captured.out.lower()
    assert "unknown-option" in captured.out
    assert "another-unknown-option" in captured.out

    # Edge case: Pass an empty list to _config_initialization
    _config_initialization(linter, [], reporter)
    captured = capsys.readouterr()
    assert "unrecognized option" not in captured.out.lower()

    # Edge case: Pass a list with a single recognized option to _config_initialization
    recognized_options = ["--help"]
    _config_initialization(linter, recognized_options, reporter)
    captured = capsys.readouterr()
    assert "unrecognized option" not in captured.out.lower()

    # Edge case: Pass a list with multiple unrecognized options to _config_initialization
    multiple_unrecognized_options = ["--unknown-option1=yes", "--unknown-option2=no", "--unknown-option3=maybe"]
    _config_initialization(linter, multiple_unrecognized_options, reporter)
    captured = capsys.readouterr()
    assert "unrecognized option" in captured.out.lower()
    assert "unknown-option1" in captured.out
    assert "unknown-option2" in captured.out
    assert "unknown-option3" in captured.out
