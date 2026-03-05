import pytest
from pylint.config.config_initialization import _config_initialization

def test_claim_c2(capsys):
    # Given: An unrecognized option 'Q' is passed to pylint.
    # When: _config_initialization is called with the unrecognized option.
    with pytest.raises(SystemExit):
        _config_initialization(['--unknown-option=yes', '-Q'])
    # Then: The linter adds a message 'unrecognized-option' with the unrecognized option name.
    output = capsys.readouterr()
    # Test captures 'unrecognized-option' message.
    assert "Unrecognized option" in output.err
    # Message includes the correct unrecognized option name.
    assert "unknown-option" in output.err
    assert "Q" in output.err
    # Test handles multiple unrecognized options.
    assert output.err.count("Unrecognized option") == 2
