import pytest
from pylint.config.config_initialization import _config_initialization, _UnrecognizedOptionError

def test_claim_c1(capsys):
    # Test raises _UnrecognizedOptionError
    # Ensure no traceback is printed
    # Verify behavior with different inputs

    # Given: Unrecognized option '-Q' is passed to _config_initialization
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(['-Q'])
    # Then: No traceback is printed
    captured = capsys.readouterr()
    assert captured.err == ""

    # Edge case: Option is empty string
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization([''])
    captured = capsys.readouterr()
    assert captured.err == ""

    # Edge case: Option is a valid option
    # Assuming a valid option for demonstration, replace with actual valid option if known
    try:
        _config_initialization(['--version'])
    except _UnrecognizedOptionError:
        pytest.fail("Valid option should not raise _UnrecognizedOptionError")

    # Edge case: Multiple unrecognized options
    with pytest.raises(_UnrecognizedOptionError):
        _config_initialization(['-Q', '-X'])
    captured = capsys.readouterr()
    assert captured.err == ""
