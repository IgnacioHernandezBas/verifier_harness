# Checklist TODO: Test fails with _UnrecognizedOptionError
# Checklist TODO: Captured output contains user-friendly error message
# Checklist TODO: No traceback is printed
import pytest
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter
from pylint.config.config_initialization import _config_initialization

def test_claim_c1(capsys):
    # Given: An unrecognized option is passed to pylint
    linter = PyLinter()
    reporter = BaseReporter()
    args_list = ['-Q']

    # When: _config_initialization is called with the unrecognized option
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)

    # Then: A _UnrecognizedOptionError is raised, and a user-friendly error message is printed
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
