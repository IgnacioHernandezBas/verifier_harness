# Checklist TODO: Custom class C with __repr__ 'x.y' is properly defined
# Checklist TODO: Symbol('x') == C() does not raise AttributeError
# Checklist TODO: Test verifies correct handling of repr-based comparisons
import pytest
import sympy
from sympy.core.symbol import Symbol

def test_claim_c1():
    # Custom class C with __repr__ 'x.y' is properly defined
    class C:
        def __repr__(self):
            return 'x.y'
    # Symbol('x') == C() does not raise AttributeError
    x = Symbol('x')
    result = x == C()
    assert result is False  # Verify comparison returns False as expected

    # Edge case: Custom class with __repr__ 'x.z'
    class D:
        def __repr__(self):
            return 'x.z'
    result = x == D()
    assert result is False

    # Edge case: Symbol 'y' compared to C()
    y = Symbol('y')
    result = y == C()
    assert result is False
