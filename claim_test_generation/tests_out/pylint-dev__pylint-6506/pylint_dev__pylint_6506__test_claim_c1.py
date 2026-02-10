import pytest
from pylint.config.config_initialization import _config_initialization, _UnrecognizedOptionError

def test_claim_c1(capsys):
    # Test raises _UnrecognizedOptionError
    # Ensure no traceback is printed
    # Verify test passes with valid setup

    # Given: Unrecognized option '-Q' is passed to _config_initialization
    args_list = ['-Q']

    # When: _config_initialization is called with an unrecognized option
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list)

    # Then: _UnrecognizedOptionError is raised without printing a traceback
    captured = capsys.readouterr()
    assert captured.err == ""

    # Edge case: Passing multiple unrecognized options
    args_list = ['-Q', '-X']
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list)
    captured = capsys.readouterr()
    assert captured.err == ""

    # Edge case: Passing a valid option along with an unrecognized one
    args_list = ['--help', '-Q']
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list)
    captured = capsys.readouterr()
    assert captured.err == ""

    # Edge case: Passing an empty list of options
    args_list = []
    _config_initialization(args_list)
    captured = capsys.readouterr()
    assert captured.err == ""
