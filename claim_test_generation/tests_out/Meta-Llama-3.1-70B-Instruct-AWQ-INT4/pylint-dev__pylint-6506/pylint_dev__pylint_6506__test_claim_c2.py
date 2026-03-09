import pytest
from pylint.config import config_initialization

def test_claim_c2(capsys):
    # GIVEN: An unrecognized option is passed to pylint.
    # WHEN: _config_initialization is called with an unrecognized option.
    # THEN: A usage tip is printed.

    # Test prints a usage tip with an unrecognized option
    # Error message includes the unrecognized option name
    # Test handles multiple unrecognized options correctly

    # Create an unrecognized option
    unrecognized_option = ["--unknown-option=yes"]

    # Call _config_initialization with the unrecognized option
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(unrecognized_option)

    # Capture the output
    captured = capsys.readouterr()

    # Check if a usage tip is printed
    assert "usage: pylint" in captured.err

    # Check if the error message includes the unrecognized option name
    assert "Unrecognized option" in captured.err

    # Test handles multiple unrecognized options correctly
    multiple_unrecognized_options = ["--unknown-option=yes", "--another-unknown-option=no"]
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(multiple_unrecognized_options)
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err

    # Pass a recognized option
    recognized_option = ["--help"]
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(recognized_option)
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.out

    # Pass no options
    no_options = []
    with pytest.raises(SystemExit):
        config_initialization._config_initialization(no_options)
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
