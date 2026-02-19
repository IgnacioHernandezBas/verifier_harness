import pytest
from pylint.checkers import misc
from pylint.lint import PyLinter

# GIVEN: Multiple note tags are specified with the --notes option.
# WHEN: Running pylint with the --notes option.
# THEN: Pylint returns a fixme warning (W0511) for each note tag.

def test_claim_c2(capsys):
    # Checklist: Test passes with multiple note tags
    # Checklist: Test passes with different note tag contents
    # Checklist: Test fails with invalid note tag format

    # Data setup: Multiple note tags specified with the --notes option
    note_tags = ["FIXME", "TODO", "XXX"]

    # Data setup: Note tags with different contents
    note_tags_with_contents = ["FIXME: fix this", "TODO: do that", "XXX: unknown"]

    # Data setup: Empty note tag
    empty_note_tag = [""]

    # Data setup: Note tag with non-punctuation characters
    note_tag_with_non_punctuation = ["FIXME123"]

    # Edge case: Single note tag
    single_note_tag = ["FIXME"]

    # Edge case: No note tags specified
    no_note_tags = []

    # Edge case: Invalid note tag format
    invalid_note_tag_format = ["Invalid"]

    # Edge case: Note tag with special characters
    note_tag_with_special_chars = ["FIXME!@#$%^&*()"]

    # Create a PyLinter object
    linter = PyLinter()

    # Set the notes option
    linter.config.notes = note_tags

    # Process tokens
    linter.check(["test.py"])

    # Capture the output
    captured = capsys.readouterr()

    # Assertion: Pylint returns a fixme warning (W0511) for each note tag
    assert "W0511" in captured.out

    # Assertion: Warning count matches the number of note tags
    assert len(note_tags) == captured.out.count("W0511")

    # Assertion: Warning messages contain note tag contents
    for note_tag in note_tags:
        assert note_tag in captured.out

    # Repeat the test with different note tag contents
    linter.config.notes = note_tags_with_contents
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" in captured.out
    assert len(note_tags_with_contents) == captured.out.count("W0511")
    for note_tag in note_tags_with_contents:
        assert note_tag in captured.out

    # Repeat the test with an empty note tag
    linter.config.notes = empty_note_tag
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Repeat the test with a note tag with non-punctuation characters
    linter.config.notes = note_tag_with_non_punctuation
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" in captured.out

    # Repeat the test with a single note tag
    linter.config.notes = single_note_tag
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" in captured.out

    # Repeat the test with no note tags specified
    linter.config.notes = no_note_tags
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Repeat the test with an invalid note tag format
    linter.config.notes = invalid_note_tag_format
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" not in captured.out

    # Repeat the test with a note tag with special characters
    linter.config.notes = note_tag_with_special_chars
    linter.check(["test.py"])
    captured = capsys.readouterr()
    assert "W0511" in captured.out
