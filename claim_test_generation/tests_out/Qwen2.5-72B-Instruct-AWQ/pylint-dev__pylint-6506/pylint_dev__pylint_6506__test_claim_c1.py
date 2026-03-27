import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter

def test_claim_c1(capsys):
    # GIVEN: An unrecognized command line option (e.g., '-Q') is provided to pylint
    linter = PyLinter()
    args_list = ["-Q"]

    # WHEN: pylint.config.config_initialization._config_initialization is called with the unrecognized option
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list)

    # THEN: The _UnrecognizedOptionError exception is raised but does not propagate to produce a traceback in the output
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err

    # Checklist:
    # - Test must raise UnrecognizedOptionError.
    # - Test must capture and check stdout and stderr.
    # - Test must not rely on internal implementation details.
