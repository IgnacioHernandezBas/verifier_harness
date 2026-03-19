# Checklist TODO: Test raises correct exception type for invalid options
# Checklist TODO: Error message includes 'Unrecognized option found'
# Checklist TODO: No traceback appears in user output
import pytest
from pylint.testutils._run import _Run

def test_claim_c1(capsys):
    # Given: An unrecognized option is passed to pylint
    # WHEN: _config_initialization is called with the unrecognized option
    with pytest.raises(SystemExit):
        _Run(["--unknown-option"], exit=False)
    # THEN: A user-friendly error message is printed without a traceback
    captured = capsys.readouterr()
    assert "usage: pylint" in captured.err
    assert "Unrecognized option" in captured.err
    # Verify no traceback appears in captured output
    assert "Traceback" not in captured.err
