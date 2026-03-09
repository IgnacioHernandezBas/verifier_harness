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
    assert result is True  # Test passes with a matching object

    # Test fails with a non-matching object
    class D:
        def __repr__(self):
            return 'y'
    assert x != D()  # Test fails with a non-matching object

    # Test handles edge cases correctly
    assert x != None  # Comparing with None
    assert x != 1  # Comparing with an object of a different type
    class E:
        def __repr__(self):
            raise Exception
    with pytest.raises(Exception):
        x == E()  # Comparing with an object with a repr that raises an exception
