import pytest
from pylint.config.config_initialization import _config_initialization, _UnrecognizedOptionError

def test_claim_c1(capsys):
    # Test raises _UnrecognizedOptionError.
    # Ensure no traceback is printed.
    # Verify behavior with various input combinations.

    # Prepare an args_list containing an unrecognized option, e.g., ['--unrecognized-option']
    args_list = ['--unrecognized-option']

    # Given: An unrecognized option is passed to pylint.
    # When: _config_initialization is called with an unrecognized option.
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list)

    # Then: _UnrecognizedOptionError is raised without printing a traceback.
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    # Edge case: Pass multiple unrecognized options.
    args_list_multiple = ['--unrecognized-option1', '--unrecognized-option2']
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list_multiple)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    # Edge case: Pass a valid option along with an unrecognized one.
    args_list_mixed = ['--output-format', 'text', '--unrecognized-option']
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list_mixed)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    # Edge case: Pass an empty args_list.
    args_list_empty = []
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(args_list_empty)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
