import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

# | GIVEN: An unrecognized option is passed to pylint.
# | WHEN: Calling pylint with an unrecognized option.
# | THEN: Pylint should print a message similar to 'unrecognized arguments: -Q'.

def test_claim_c2(capsys):
    # Test passes unrecognized option to _config_initialization
    # Test verifies required positional args from signatures
    # Test checks for user-friendly error message

    # Create an instance of PyLinter
    linter = PyLinter()

    # Create an instance of BaseReporter
    reporter = BaseReporter()

    # Pass unrecognized option to _config_initialization
    _config_initialization(linter, ["--unknown-option=yes"], reporter)

    # Capture the output
    captured = capsys.readouterr()

    # Check for user-friendly error message
    assert "unrecognized arguments" in captured.err

    # Edge cases
    # Pass multiple unrecognized options
    _config_initialization(linter, ["--unknown-option=yes", "--another-unknown-option=no"], reporter)
    captured = capsys.readouterr()
    assert "unrecognized arguments" in captured.err

    # Pass no options
    _config_initialization(linter, [], reporter)
    captured = capsys.readouterr()
    assert "unrecognized arguments" not in captured.err

    # Pass valid options
    _config_initialization(linter, ["--help"], reporter)
    captured = capsys.readouterr()
    assert "unrecognized arguments" not in captured.err
