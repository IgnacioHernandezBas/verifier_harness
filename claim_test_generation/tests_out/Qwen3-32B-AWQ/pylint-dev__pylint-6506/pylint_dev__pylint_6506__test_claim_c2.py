# Checklist TODO: Simulate invalid CLI option invocation
# Checklist TODO: Verify exact error message format in output
# Checklist TODO: Confirm no crashes in argument parsing
import pytest

def test_claim_c2(capsys):
    # GIVEN: An unrecognized option is passed to pylint
    from pylint.lint import Run
    
    # WHEN: Calling pylint with an unrecognized option
    with pytest.raises(SystemExit):
        Run(["-Q"], exit=False)
    
    # THEN: Pylint should print a message similar to 'unrecognized arguments: -Q'
    captured = capsys.readouterr()
    assert "unrecognized arguments: -Q" in captured.err
    assert "unrecognized-option" in captured.err
    assert "Traceback" not in captured.err  # No traceback leakage in output

    # Edge case: Mixed valid/invalid options
    with pytest.raises(SystemExit):
        Run(["--help", "-Q"], exit=False)
    captured = capsys.readouterr()
    assert "unrecognized arguments: -Q" in captured.err
    assert "unrecognized-option" in captured.err
    assert "Traceback" not in captured.err

    # Edge case: Long-form unrecognized option
    with pytest.raises(SystemExit):
        Run(["--quilt"], exit=False)
    captured = capsys.readouterr()
    assert "unrecognized arguments: --quilt" in captured.err
    assert "unrecognized-option" in captured.err
    assert "Traceback" not in captured.err
