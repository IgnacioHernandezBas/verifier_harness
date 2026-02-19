import pytest
from pylint.lint import PyLinter
from pylint.config import config_initialization
from pylint.reporters import BaseReporter

# Test raises _UnrecognizedOptionError without traceback
# Test handles multiple unrecognized options
# Test handles valid options correctly

def test_claim_c1(capsys):
    # GIVEN: An unrecognized option is passed to pylint.
    # WHEN: Calling pylint with an unrecognized option.
    # THEN: Pylint should raise an _UnrecognizedOptionError without a traceback.

    # Pass unrecognized option to pylint
    # Verify _config_initialization is called with args_list
    linter = PyLinter()
    reporter = BaseReporter()
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, ["--unknown-option=yes"], reporter)
    captured = capsys.readouterr()
    assert "Unrecognized option" in captured.err

    # Pass multiple unrecognized options
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, ["--unknown-option=yes", "--another-unknown-option"], reporter)
    captured = capsys.readouterr()
    assert "Unrecognized option" in captured.err

    # Pass no options
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, [], reporter)
    captured = capsys.readouterr()
    assert "Unrecognized option" not in captured.err

    # Pass valid options
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(linter, ["--help"], reporter)
    captured = capsys.readouterr()
    assert "Unrecognized option" not in captured.err
