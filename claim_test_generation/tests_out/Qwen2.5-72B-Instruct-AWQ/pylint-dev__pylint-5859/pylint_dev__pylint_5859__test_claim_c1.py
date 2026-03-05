# Checklist TODO: Test file contains only punctuation in a note tag.
# Checklist TODO: Pylint is run with the --notes option.
# Checklist TODO: Pylint outputs a fixme warning for the note tag.
import pytest
from pylint.checkers.misc import MiscChecker
from pylint.lint import PyLinter
from pylint.config import ConfigurationMixIn
from pylint.reporters import BaseReporter

# Test _check_encoding and process_tokens with note tags as punctuation.
def test_claim_c1(tmpdir, monkeypatch, capsys):
    # GIVEN: A note tag specified with the --notes option is entirely punctuation.
    # Create a test file with a note tag entirely composed of punctuation.
    test_file = tmpdir.join("test.py")
    test_file.write("a = 1\n#???\n")

    # Ensure the test file is in the directory where pylint will be run.
    monkeypatch.chdir(tmpdir)

    # Configure pylint to use the --notes option with the punctuation note tag.
    linter = PyLinter()
    linter.set_option("notes", ["???"])
    linter.set_reporter(BaseReporter())
    checker = MiscChecker(linter)
    linter.register_checker(checker)

    # WHEN: Running pylint with the --notes option.
    linter.check(["test.py"])

    # THEN: Pylint returns a fixme warning (W0511) for the note tag.
    captured = capsys.readouterr()
    assert "W0511: Fixme" in captured.out
    assert "line 2" in captured.out
    assert "col 17" in captured.out
    assert "????" in captured.out

    # The warning message includes the note tag entirely composed of punctuation.
    assert "????" in captured.out

    # No other warnings are raised for the test file.
    assert "W0511" in captured.out
    assert captured.out.count("W0511") == 1

    # Test with a note tag that is an empty string.
    test_file.write("a = 1\n#")
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Test with a note tag that contains spaces and punctuation.
    test_file.write("a = 1\n# ? ?")
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Test with a note tag that contains alphanumeric characters and punctuation.
    test_file.write("a = 1\n# ???123")
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out
