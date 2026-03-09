# Checklist TODO: Test must simulate an unrecognized option being passed.
# Checklist TODO: Capture and assert the output contains a usage tip.
# Checklist TODO: Ensure no exceptions are raised during the test.
import pytest
from pylint.config.config_initialization import _config_initialization

def test_claim_c2(capsys):
    # GIVEN: An unrecognized option is passed to pylint.
    args = ["pylint", "--unknown-option=yes"]

    # WHEN: _config_initialization is called with an unrecognized option.
    try:
        _config_initialization(args)
    except SystemExit:
        pass

    # THEN: A usage tip is printed to stdout.
    output = capsys.readouterr()
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Ensure no exceptions are raised during the test.
    # Note: SystemExit is expected and caught, so no other exceptions should occur.
