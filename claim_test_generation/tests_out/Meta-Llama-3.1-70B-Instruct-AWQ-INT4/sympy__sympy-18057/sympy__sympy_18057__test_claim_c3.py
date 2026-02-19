import pytest
from sympy import Symbol

def test_claim_c3(capsys):
    # Given: A SymPy Symbol and an object with a repr that evaluates to the same symbol.
    x = Symbol('x')
    class C:
        def __repr__(self):
            return 'x'

    # When: sympy.Symbol('x') == C()
    result = x == C()

    # Then: The comparison returns True.
    assert result is True

    # Test passes when comparing a SymPy Symbol to an object with a matching repr
    # Test fails when comparing a SymPy Symbol to an object with a non-matching repr
    class D:
        def __repr__(self):
            return 'y'
    assert x != D()

    # Test handles edge cases correctly
    assert x != None
    assert x != Symbol('y')
    assert x != 'x'

    # The comparison with a non-matching object returns False
    assert x != D()
