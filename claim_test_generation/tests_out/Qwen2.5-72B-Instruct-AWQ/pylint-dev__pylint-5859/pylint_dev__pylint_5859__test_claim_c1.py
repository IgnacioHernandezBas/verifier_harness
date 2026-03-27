# Checklist TODO: Create a test file with specific note tags.
# Checklist TODO: Run pylint with custom --notes option.
# Checklist TODO: Capture and assert the expected warnings.
import pytest
from pylint.lint import Run
from pylint.config import ConfigurationMixIn

def test_claim_c1(tmpdir, monkeypatch, capsys):
    # Create a test file with specific note tags
    test_file = tmpdir.join("test.py")
    test_file.write("""
    #YES
    #???
    """)

    # Set up the environment to run pylint with --notes="YES,???"
    monkeypatch.setattr(ConfigurationMixIn, "notes", ["YES", "???"])

    # Run pylint with custom --notes option
    args = [str(test_file), "--notes=YES,???"]
    Run(args)

    # Capture and assert the expected warnings
    captured = capsys.readouterr()
    output = captured.out + captured.err

    # Pylint outputs a W0511 warning for 'YES'.
    assert "W0511: YES" in output
    # Pylint outputs a W0511 warning for '???'.
    assert "W0511: ???" in output
    # No other warnings are emitted.
    assert len(output.splitlines()) == 2
