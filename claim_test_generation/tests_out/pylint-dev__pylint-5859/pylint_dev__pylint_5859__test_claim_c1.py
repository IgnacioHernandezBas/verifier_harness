# Chosen strategy: unit
# Key observable(s) asserted: fixme warnings for both lines
# Inputs/fixtures used: mock tokens with '# YES: yes' and '# ???: no'

import pytest
from pylint.checkers.misc import BaseTokenChecker
from pylint.utils import TokenInfo

def test_claim_c1():
    # Given
    tokens = [
        TokenInfo(type=54, string='# YES: yes', start=(1, 0), end=(1, 11), line='# YES: yes\n'),
        TokenInfo(type=54, string='# ???: no', start=(2, 0), end=(2, 10), line='# ???: no\n')
    ]
    checker = BaseTokenChecker()
    checker.config.notes = ['YES', '???']

    # When
    checker.process_tokens(tokens)

    # Then
    assert len(checker.linter.msgs_store.messages) == 2
    assert any(msg.msg == 'YES: yes' for msg in checker.linter.msgs_store.messages)
    assert any(msg.msg == '???: no' for msg in checker.linter.msgs_store.messages)
