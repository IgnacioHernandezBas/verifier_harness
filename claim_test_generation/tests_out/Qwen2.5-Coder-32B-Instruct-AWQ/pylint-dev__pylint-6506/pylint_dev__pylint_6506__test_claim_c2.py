import pytest
from pylint.lint import Run as LintRun

def test_claim_c2(capsys):
    # Test captures 'unrecognized arguments: -Q' in output.
    # Given: An unrecognized option '-Q' is passed to pylint.
    # When: Calling pylint with an unrecognized option.
    with pytest.raises(SystemExit):
        LintRun(["-Q"], exit=False)
    output = capsys.readouterr()
    # Then: Pylint should print a message similar to 'unrecognized arguments: -Q'.
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Test handles multiple unrecognized options correctly.
    # Given: Multiple unrecognized options are passed to pylint.
    # When: Calling pylint with multiple unrecognized options.
    with pytest.raises(SystemExit):
        LintRun(["-Q", "--unknown-option"], exit=False)
    output = capsys.readouterr()
    # Then: Pylint should print a message similar to 'unrecognized arguments: -Q, --unknown-option'.
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Test distinguishes between valid and invalid options.
    # Given: A valid option along with an unrecognized one is passed to pylint.
    # When: Calling pylint with a valid and an unrecognized option.
    with pytest.raises(SystemExit):
        LintRun(["--help", "-Q"], exit=False)
    output = capsys.readouterr()
    # Then: Pylint should print a message similar to 'unrecognized arguments: -Q'.
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err

    # Given: An option that is a prefix of a valid option is passed to pylint.
    # When: Calling pylint with a prefix of a valid option.
    with pytest.raises(SystemExit):
        LintRun(["--hel"], exit=False)
    output = capsys.readouterr()
    # Then: Pylint should print a message similar to 'unrecognized arguments: --hel'.
    assert "usage: pylint" in output.err
    assert "Unrecognized option" in output.err
