# Checklist TODO: Symbol and custom object with same repr are not equal
# Checklist TODO: Equality check correctly distinguishes objects by type
# Checklist TODO: Repr implementation doesn't affect equality outcome
import pytest
import sympy
from sympy.core.expr import Expr

def test_claim_c2():
    # Given: An unknown object whose repr is 'x'
    class C:
        def __repr__(self):
            return 'x'
    c = C()
    x = sympy.Symbol('x')
    # When: Calling sympy.Symbol('x') == C()
    result = x == c
    # Then: Returns False
    assert result is False
    # Check that the repr is correctly implemented
    assert repr(c) == 'x'
    # Edge case: Different symbol name vs identical repr
    y = sympy.Symbol('y')
    assert y == c is False
