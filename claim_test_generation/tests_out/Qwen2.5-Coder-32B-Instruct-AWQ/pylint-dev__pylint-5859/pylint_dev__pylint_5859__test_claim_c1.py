import pytest
from pylint.checkers.misc import MiscChecker
from pylint.utils import tokenize_str

def test_claim_c1(monkeypatch):
    # Function processes tokens correctly with specified notes.
    # Output includes fixme warnings for both lines.
    # Function handles edge cases gracefully.

    # Given: The --notes option is set to include 'YES,???' and the source file contains '# YES: yes' and '# ???: no'.
    monkeypatch.setattr(MiscChecker, 'config', type('Config', (object,), {'notes': ['YES', '???']}))

    # Create an instance of MiscChecker
    checker = MiscChecker()

    # Create tokens containing '# YES: yes' and '# ???: no'
    code = """a = 1
# YES: yes
# ???: no
"""
    tokens = list(tokenize_str(code))

    # When: pylint.process_tokens is called with tokens containing '# YES: yes' and '# ???: no'.
    with pytest.raises(AssertionError) as excinfo:
        # Check for W0511: YES: yes (fixme) in the output.
        # Check for W0511: ???: no (fixme) in the output.
        checker.process_tokens(tokens)

    # Then: pylint should return fixme warnings for both lines.
    assert "W0511: YES: yes (fixme)" in str(excinfo.value)
    assert "W0511: ???: no (fixme)" in str(excinfo.value)

    # Edge case: Test with empty tokens list
    empty_tokens = []
    checker.process_tokens(empty_tokens)  # Should not raise any exceptions

    # Edge case: Test with no --notes option set
    monkeypatch.setattr(MiscChecker, 'config', type('Config', (object,), {'notes': []}))
    checker.process_tokens(tokens)  # Should not raise any exceptions

    # Edge case: Test with --notes option not including 'YES,???'
    monkeypatch.setattr(MiscChecker, 'config', type('Config', (object,), {'notes': ['TODO']}))
    checker.process_tokens(tokens)  # Should not raise any exceptions
