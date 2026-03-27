# Checklist TODO: Test shows unrecognized option triggers E0015 message
# Checklist TODO: Message includes the exact unrecognized option name
# Checklist TODO: Error message format matches pylint's standard reporting
import pytest
from pylint.testutils._run import _Run

def test_claim_c2(capsys):
    # Given: An unrecognized option is passed to pylint
    # When: _config_initialization is called with the unrecognized option
    with pytest.raises(SystemExit) as exc_info:
        _Run(["--unknown-option=yes"], exit=False)
    # Then: The linter adds a message 'unrecognized-option' with the unrecognized option name
    captured = capsys.readouterr()
    assert "unrecognized-option" in captured.err
    assert "unknown-option=yes" in captured.err
    assert exc_info.value.code != 0
