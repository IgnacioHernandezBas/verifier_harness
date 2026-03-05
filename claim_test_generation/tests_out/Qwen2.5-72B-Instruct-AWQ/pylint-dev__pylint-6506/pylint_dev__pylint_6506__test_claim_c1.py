# Checklist TODO: Test must mock the linter and args_list parameters.
# Checklist TODO: Test must capture and check the output for no traceback.
# Checklist TODO: Test must verify the error message includes the unrecognized option.
import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter

def test_claim_c1(monkeypatch, capsys):
    # GIVEN: An unrecognized option is passed to pylint.
    # Create a mock linter object to pass to _config_initialization.
    linter = PyLinter()

    # Prepare a list of arguments including an unrecognized option.
    args_list = ["--unknown-option=yes"]

    # Monkeypatch sys.argv to include the unrecognized option.
    monkeypatch.setattr("sys.argv", ["pylint"] + args_list)

    # WHEN: Calling pylint with an unrecognized option.
    # THEN: Pylint should raise an _UnrecognizedOptionError without a traceback.
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list)

    # Capture and check the output for no traceback.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Verify the error message includes the unrecognized option.
    assert "unknown-option" in output.err

    # Edge cases
    # Pass an empty string as an unrecognized option.
    args_list = ["--"]
    monkeypatch.setattr("sys.argv", ["pylint"] + args_list)
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Pass a non-string value as an unrecognized option.
    args_list = ["-1"]
    monkeypatch.setattr("sys.argv", ["pylint"] + args_list)
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Pass multiple unrecognized options.
    args_list = ["--unknown-option1=yes", "--unknown-option2=no"]
    monkeypatch.setattr("sys.argv", ["pylint"] + args_list)
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    assert "unknown-option1" in output.err
    assert "unknown-option2" in output.err
