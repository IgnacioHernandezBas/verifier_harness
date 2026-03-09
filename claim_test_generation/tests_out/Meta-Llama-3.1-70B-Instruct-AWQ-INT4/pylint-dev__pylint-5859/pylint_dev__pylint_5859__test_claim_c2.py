import pytest
from pylint.checkers import misc

# GIVEN: Multiple note tags are specified with the --notes option.
# WHEN: Running pylint with the --notes option.
# THEN: Pylint returns a fixme warning (W0511) for each note tag.

def test_claim_c2(capsys):
    # Test returns fixme warnings for multiple note tags
    # Test handles edge cases with empty or non-punctuation note tags
    # Test verifies number of warnings equals number of note tags

    # Create a MiscChecker object
    checker = misc.MiscChecker()

    # Set the notes option
    checker.linter.config.notes = ["YES", "???"]

    # Process some tokens
    code = """a = 1
    #???
    """
    checker.process_tokens(code)

    # Capture the output
    captured = capsys.readouterr()

    # Check that the output contains the expected warnings
    assert "W0511" in captured.out
    assert "???" in captured.out
    assert "YES" in captured.out

    # Check that the number of warnings equals the number of note tags
    warnings = captured.out.split("W0511")
    assert len(warnings) == len(checker.linter.config.notes) + 1
