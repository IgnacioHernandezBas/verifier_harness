# Checklist TODO: Test shows exception is raised but contained
# Checklist TODO: Output validation confirms no traceback leakage
# Checklist TODO: Error message matches expected pattern
import pytest
from pylint.lint import Run as LintRun

def test_claim_c1(capsys):
    # GIVEN: An unrecognized command line option '-Q'
    # WHEN: _config_initialization is invoked with the option
    # THEN: Exception is raised but no traceback appears in output
    with pytest.raises(SystemExit):
        LintRun(["-Q"], exit=False)
    
    captured = capsys.readouterr()
    
    # Check exception is handled and no traceback appears
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err
    assert "Traceback" not in captured.err
