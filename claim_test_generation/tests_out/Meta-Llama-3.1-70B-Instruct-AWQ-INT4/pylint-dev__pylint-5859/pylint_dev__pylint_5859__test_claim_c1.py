import pytest
from pylint import lint
from pylint.checkers import misc
from pylint.config import Configuration

# Given: A Python file containing a comment line with a note tag consisting entirely of punctuation (e.g., '???')
# When: Running pylint with --notes="YES,???" on the file
# Then: Pylint outputs a W0511 warning for both the 'YES' and '???' note tags

def test_claim_c1(capsys):
    # Checklist: Test emits W0511 warning for 'YES' note tag
    # Checklist: Test emits W0511 warning for '???' note tag
    # Checklist: Test handles note tags with punctuation correctly

    # Data setup: Create a Python file with a comment line containing a note tag consisting entirely of punctuation
    code = """# YES: yes
# ???: no"""

    # Data setup: Run pylint with --notes="YES,???" on the file
    config = Configuration()
    config.notes = ["YES", "???"]
    linter = lint.PyLinter()
    linter.set_option('notes', config.notes)
    linter.check([misc.MiscChecker(linter)])
    linter.check([code])

    # Assertions: Pylint outputs a W0511 warning for both the 'YES' and '???' note tags
    captured = capsys.readouterr()
    assert "W0511: YES: yes" in captured.out
    assert "W0511: ???: no" in captured.out

    # Edge cases: Empty note tags
    config.notes = [""]
    linter = lint.PyLinter()
    linter.set_option('notes', config.notes)
    linter.check([misc.MiscChecker(linter)])
    linter.check([code])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Edge cases: Note tags with only whitespace
    config.notes = ["   "]
    linter = lint.PyLinter()
    linter.set_option('notes', config.notes)
    linter.check([misc.MiscChecker(linter)])
    linter.check([code])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Edge cases: Note tags with non-punctuation characters
    config.notes = ["abc"]
    linter = lint.PyLinter()
    linter.set_option('notes', config.notes)
    linter.check([misc.MiscChecker(linter)])
    linter.check([code])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out
