import pytest
from pylint.checkers import misc

def test_claim_c1():
    # Given
    assert hasattr(misc, 'process_tokens')
    tokens = ['# YES: yes', '# ???: no']
    checker = misc.MiscChecker(None)
    checker.config.notes = ['YES', '???']

    # When
    messages = list(checker.process_tokens(tokens))

    # Then
    assert len(messages) == 2
