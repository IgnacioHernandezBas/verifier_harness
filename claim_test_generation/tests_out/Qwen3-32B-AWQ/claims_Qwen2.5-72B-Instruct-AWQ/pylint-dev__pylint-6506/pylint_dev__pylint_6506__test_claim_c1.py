# Checklist TODO: Verify error message is user-friendly
# Checklist TODO: Confirm no traceback is displayed
# Checklist TODO: Ensure proper exit code on invalid option
import pytest
from pylint.lint import Run

def test_claim_c1(capsys):
    # GIVEN: CLI arguments with an unrecognized option "-Q"
    # WHEN: Config initialization is triggered via Run
    # THEN: Error message is printed without traceback and process exits non-zero
    with pytest.raises(SystemExit) as exc_info:
        Run(["-Q"], exit=False)
    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    # Check for user-friendly error message
    assert "Unrecognized option found" in combined_output
    # Ensure no traceback is present
    assert "Traceback" not in combined_output
    # Verify non-zero exit code
    assert exc_info.value.code != 0
