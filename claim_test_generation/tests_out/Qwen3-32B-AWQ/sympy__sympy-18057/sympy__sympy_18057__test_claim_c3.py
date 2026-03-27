# Checklist TODO: Uses 'from sympy import Symbol' instead of core.expr
# Checklist TODO: Comparison returns True for valid repr match
# Checklist TODO: No forbidden fixtures in test implementation
import pytest
from sympy import Symbol

def test_claim_c3():
    # Given: A SymPy Symbol and an object with a repr that evaluates to the same symbol.
    class C:
        def __repr__(self):
            return 'x'
    x = Symbol('x')
    c = C()

    # When: sympy.Symbol('x') == C()
    result = x == c

    # Then: The comparison returns True.
    assert result is True

    # Verify __repr__ of C() returns 'x'
    assert repr(c) == 'x'

    # Confirm Symbol is imported from sympy package
    assert isinstance(x, Symbol)
