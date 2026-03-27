# Checklist TODO: Uses 'from sympy import Symbol' instead of core.expr
# Checklist TODO: Compares Symbol to custom object with matching repr
# Checklist TODO: Verifies equality returns True for valid symbol/repr pair
import pytest
from sympy import Symbol

def test_claim_c3():
    # Given: A SymPy Symbol and an object with a repr that evaluates to the same symbol
    x = Symbol('x')
    class C:
        def __repr__(self):
            return 'x'
    c = C()

    # When: Comparing the Symbol to the object
    result = x == c

    # Then: The comparison returns True
    assert result is True

    # Additional assertions from the test sketch
    assert type(x) is Symbol
    assert repr(c) == 'x'
