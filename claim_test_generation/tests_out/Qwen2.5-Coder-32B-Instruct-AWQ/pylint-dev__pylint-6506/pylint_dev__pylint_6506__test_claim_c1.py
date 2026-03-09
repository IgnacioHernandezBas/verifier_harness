# Checklist TODO: Test raises _UnrecognizedOptionError
# Checklist TODO: Ensure no traceback is printed
# Checklist TODO: Verify behavior with various inputs
import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

def test_claim_c1(capsys):
    # Given: An unrecognized option is passed to pylint.
    linter = PyLinter()
    reporter = BaseReporter()
    args_list = ['-Q']

    # When: _config_initialization is called with an unrecognized option.
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)

    # Then: _UnrecognizedOptionError is raised without printing a traceback.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Verify behavior with various inputs
    # Edge case: Passing multiple unrecognized options
    args_list = ['-Q', '--unknown-option']
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Passing a valid option along with an unrecognized one
    args_list = ['--output-format=text', '--unknown-option']
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Passing an empty list of options
    args_list = []
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" not in output.err
