# Checklist TODO: Test captures a usage tip message.
# Checklist TODO: Usage tip includes information about the unrecognized option.
# Checklist TODO: Test handles multiple and mixed options correctly.
import pytest
from pylint.config.config_initialization import _config_initialization

def test_claim_c2(capsys):
    # Given: An unrecognized option is passed to pylint.
    # When: _config_initialization is called with an unrecognized option.
    with pytest.raises(SystemExit):
        _config_initialization(["--unknown-option=yes"])
    
    # Then: A usage tip is printed.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass multiple unrecognized options.
    with pytest.raises(SystemExit):
        _config_initialization(["--unknown-option1", "--unknown-option2"])
    
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass a valid option along with an unrecognized one.
    with pytest.raises(SystemExit):
        _config_initialization(["--output-format=text", "--unknown-option"])
    
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Edge case: Pass an empty string as an option.
    with pytest.raises(SystemExit):
        _config_initialization([""])
    
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
