# Checklist TODO: Test verifies correct exception type is raised
# Checklist TODO: Confirms traceback absence in error output
# Checklist TODO: Validates error message contains option identifier
import pytest
from pylint.testutils._run import _Run as Run
from pylint.config.exceptions import _UnrecognizedOptionError

def test_claim_c1(tmp_path, capsys):
    # Given: An unrecognized option '-Q' is passed
    dummy_file = tmp_path / "dummy.py"
    dummy_file.touch()
    # When: Calling pylint with an unrecognized option
    with pytest.raises(SystemExit):
        Run([str(dummy_file), "-Q"], exit=False)
    # Then: Pylint should raise an _UnrecognizedOptionError without a traceback
    captured = capsys.readouterr()
    assert "Unrecognized option found: Q" in captured.err
    assert "Traceback" not in captured.err
