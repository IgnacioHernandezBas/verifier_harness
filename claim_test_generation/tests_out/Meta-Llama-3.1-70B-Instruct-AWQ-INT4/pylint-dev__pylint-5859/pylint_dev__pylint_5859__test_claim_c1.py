import pytest
from pylint.checkers import misc
from pylint.lint import PyLinter

# | GIVEN: A note tag specified with the --notes option is entirely punctuation.
# | WHEN: Running pylint with the --notes option.
# | THEN: Pylint returns a fixme warning (W0511) for the note tag.

def test_claim_c1(capsys):
    # Checklist: Test passes with a note tag containing only punctuation
    # Checklist: Test fails with a note tag containing non-punctuation characters
    # Checklist: Test handles multiple note tags correctly

    # Data setup: Create a note tag with entirely punctuation
    note_tag = "???"
    
    # Data setup: Run pylint with the --notes option
    linter = PyLinter()
    linter.set_option('notes', [note_tag])
    
    # Exercise _check_encoding, process_tokens with parameters
    linter.check(['test.py'])
    
    # Assertions: Pylint returns a fixme warning (W0511) for the note tag
    # Assertions: Warning message contains the note tag text
    captured = capsys.readouterr()
    assert "W0511:" in captured.out
    assert note_tag in captured.out

    # Edge case: Empty note tag
    linter.set_option('notes', [""])
    linter.check(['test.py'])
    captured = capsys.readouterr()
    assert "W0511:" not in captured.out

    # Edge case: Note tag with non-punctuation characters
    linter.set_option('notes', ["abc"])
    linter.check(['test.py'])
    captured = capsys.readouterr()
    assert "W0511:" not in captured.out

    # Edge case: Multiple note tags with different contents
    linter.set_option('notes', ["???", "abc"])
    linter.check(['test.py'])
    captured = capsys.readouterr()
    assert "W0511:" in captured.out
    assert "???" in captured.out
    assert "abc" not in captured.out
