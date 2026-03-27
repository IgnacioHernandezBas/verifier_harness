# Checklist TODO: Test shows error raised for invalid option
# Checklist TODO: Confirms no traceback is printed
# Checklist TODO: Verifies correct error message pattern
import pytest
from pylint.lint import Run

def test_claim_c1(capsys):
    # GIVEN: An unrecognized option is passed to pylint
    # WHEN: _config_initialization is called with an unrecognized option
    with pytest.raises(SystemExit):
        Run(["-Q"], exit=False)
    # THEN: _UnrecognizedOptionError is raised without printing a traceback
    captured = capsys.readouterr()
    # Error message contains 'unrecognized-option' warning
    assert "Unrecognized option" in captured.err
    # No traceback appears in captured output
    assert "Traceback" not in captured.err
    # Process exits with non-zero status code (implied by SystemExit)
