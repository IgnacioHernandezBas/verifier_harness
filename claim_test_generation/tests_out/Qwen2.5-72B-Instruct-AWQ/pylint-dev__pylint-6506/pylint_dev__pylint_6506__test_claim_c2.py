import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter

# Test must mock linter and args_list.
# Test must capture and check the printed error message.
# Test must verify the exit status code.

def test_claim_c2(monkeypatch, capsys):
    # Mock a linter object with necessary attributes and methods.
    linter = PyLinter()

    # Prepare an args_list with an unrecognized option '-Q'.
    args_list = ["-Q"]

    # Mock the sys.exit to avoid actual program termination
    monkeypatch.setattr("sys.exit", lambda status: None)

    # Call _config_initialization with the mocked linter and args_list.
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list)

    # Capture the output and check the printed error message.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Verify the exit status code.
    assert "sys.exit" in monkeypatch._mocks
    assert monkeypatch._mocks["sys.exit"].call_args[0][0] != 0
