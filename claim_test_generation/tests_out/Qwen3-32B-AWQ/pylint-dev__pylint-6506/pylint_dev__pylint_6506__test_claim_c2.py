# Checklist TODO: Test verifies error message is generated for invalid options
# Checklist TODO: Message includes exact unrecognized option name
# Checklist TODO: Error code matches pylint's documented 'unrecognized-option' message
import pytest
from pylint.testutils._run import _Run as Run

def test_claim_c2(capsys):
    # Given: An unrecognized option is passed to pylint
    # When: _config_initialization is called with the unrecognized option
    with pytest.raises(SystemExit):
        Run(["--unrecognized-option=test"], exit=False)
    # Then: The linter adds a message 'unrecognized-option' with the unrecognized option name
    captured = capsys.readouterr()
    # Assertion: Captured output contains 'E0015: Unrecognized option found: unrecognized-option=test'
    assert "E0015: Unrecognized option found: unrecognized-option=test" in captured.err
    # Assertion: Error message code matches expected 'unrecognized-option' symbol
    assert "(unrecognized-option)" in captured.err
