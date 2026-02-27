import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import Run as LintRun

def test_claim_c1(capsys):
    # Prepare an unrecognized option for pylint
    unrecognized_option = "--unknown-option=yes"
    
    # Test raises _UnrecognizedOptionError for unrecognized option
    with pytest.raises(SystemExit):
        LintRun([unrecognized_option], exit=False)
    
    # Ensure no traceback is printed in the output
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    assert "Traceback" not in output.err

    # Verify behavior with multiple unrecognized options
    multiple_unrecognized_options = ["--unknown-option1=yes", "--unknown-option2=no"]
    with pytest.raises(SystemExit):
        LintRun(multiple_unrecognized_options, exit=False)
    
    # Ensure no traceback is printed in the output
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    assert "Traceback" not in output.err

    # Verify behavior with a valid option along with an unrecognized one
    valid_option = "--disable=C0114"
    mixed_options = [valid_option, unrecognized_option]
    with pytest.raises(SystemExit):
        LintRun(mixed_options, exit=False)
    
    # Ensure no traceback is printed in the output
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    assert "Traceback" not in output.err
