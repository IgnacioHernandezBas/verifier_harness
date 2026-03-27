import pytest
from pylint.config.config_initialization import _config_initialization
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

def test_claim_c1(capsys):
    # Prepare a list containing an unrecognized command line option, e.g., ['-Q']
    unrecognized_option = ['-Q']
    
    # Create an instance of PyLinter
    linter = PyLinter()
    
    # Create an instance of BaseReporter
    reporter = BaseReporter()
    
    # Test raises _UnrecognizedOptionError for invalid input.
    with pytest.raises(SystemExit):
        _config_initialization(linter, unrecognized_option, reporter)
    
    # Ensure no traceback is printed in the output.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    
    # Verify behavior with various combinations of options.
    # Test with multiple unrecognized options.
    multiple_unrecognized_options = ['-Q', '--unknown-option']
    with pytest.raises(SystemExit):
        _config_initialization(linter, multiple_unrecognized_options, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    
    # Test with a valid option followed by an unrecognized one.
    valid_and_unrecognized_options = ['--help', '-Q']
    with pytest.raises(SystemExit):
        _config_initialization(linter, valid_and_unrecognized_options, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
    
    # Test with no options at all.
    no_options = []
    with pytest.raises(SystemExit):
        _config_initialization(linter, no_options, reporter)
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" not in output.err
