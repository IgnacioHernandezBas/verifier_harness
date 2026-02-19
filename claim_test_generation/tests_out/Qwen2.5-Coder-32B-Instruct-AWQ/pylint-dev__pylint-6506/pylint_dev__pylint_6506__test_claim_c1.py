# Checklist TODO: Test raises _UnrecognizedOptionError
# Checklist TODO: Verify no traceback in output
# Checklist TODO: Ensure valid options do not raise error
import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

def test_claim_c1(capsys):
    # Given: An unrecognized option is passed to pylint.
    args_list = ['-Q']
    linter = PyLinter()
    reporter = BaseReporter()

    # When: _config_initialization is called with an unrecognized option.
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)

    # Then: _UnrecognizedOptionError is raised without printing a traceback.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass multiple unrecognized options
    args_list_multiple = ['-Q', '--unknown-option']
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list_multiple, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass a valid option to ensure no false positives
    args_list_valid = ['--help']
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list_valid, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" not in output.err

    # Edge case: Test with an empty list to see if it handles no options gracefully
    args_list_empty = []
    _config_initialization(linter, args_list_empty, reporter)
    output = capsys.readouterr()
    assert output.err == ""
