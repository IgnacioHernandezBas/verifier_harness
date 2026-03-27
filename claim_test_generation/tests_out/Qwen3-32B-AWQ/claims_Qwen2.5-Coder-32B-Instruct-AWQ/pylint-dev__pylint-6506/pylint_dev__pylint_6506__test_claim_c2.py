# Checklist TODO: Test verifies error output presence
# Checklist TODO: Test avoids internal exception references
# Checklist TODO: Test confirms correct error message pattern
import pytest
from pylint.lint import Run as LintRun

def test_claim_c2(capsys: pytest.CaptureFixture) -> None:
    # GIVEN: An unrecognized option is passed to pylint
    # WHEN: _config_initialization is called with an unrecognized option
    # THEN: A usage tip is printed
    with pytest.raises(SystemExit):
        LintRun(["nonexistent_module", "--invalid-option"], exit=False)
    captured = capsys.readouterr()
    # Captured stderr contains 'usage: ' prefix indicating command-line help
    assert "usage: pylint" in captured.err
    # Error message includes 'unrecognized arguments' pattern
    assert "unrecognized arguments" in captured.err
    # Output contains the exact unrecognized option from test input
    assert "--invalid-option" in captured.err
