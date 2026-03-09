# Checklist TODO: Test prints usage tip for unrecognized option.
# Checklist TODO: Ensure no usage tip for valid option.
# Checklist TODO: Verify behavior with no options.
import pytest
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter
from pylint.config.config_initialization import _config_initialization

def test_claim_c2(capsys):
    # Given: An unrecognized option is passed to pylint.
    linter = PyLinter()
    reporter = BaseReporter()
    args_list = ['-Q']

    # When: _config_initialization is called with an unrecognized option.
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)

    # Then: A usage tip is printed.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass multiple unrecognized options.
    args_list = ['-Q', '--unknown-option']
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)

    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass a valid option to ensure no usage tip is printed.
    args_list = ['--help']
    with pytest.raises(SystemExit):
        _config_initialization(linter, args_list, reporter)

    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" not in output.err

    # Edge case: Pass no options to see if it behaves as expected.
    args_list = []
    _config_initialization(linter, args_list, reporter)

    output = capsys.readouterr()
    assert "usage: pylint" not in output.err
    assert "Unrecognized option" not in output.err
