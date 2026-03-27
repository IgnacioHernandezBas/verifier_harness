# Checklist TODO: Verify W0511 warning for punctuation-only note tag
# Checklist TODO: Confirm output capture with capsys
# Checklist TODO: Test runs in isolated tmpdir environment
import pytest
from pylint.checkers.misc import MiscChecker
import tokenize
from io import StringIO

def test_claim_c1():
    # GIVEN: A note tag specified with the --notes option is entirely punctuation.
    checker = MiscChecker()
    checker.config.notes = ["???"]
    code = """a = 1
            #???
            """
    # WHEN: Running pylint with the --notes option.
    tokens = list(tokenize.generate_tokens(StringIO(code).readline))
    checker.process_tokens(tokens)
    # THEN: Pylint returns a fixme warning (W0511) for the note tag.
    # Check for the presence of the expected message
    assert any(
        msg[1] == 2 and msg[2] == "fixme" and msg[3] == "???"
        for msg in checker._msgs
    )
