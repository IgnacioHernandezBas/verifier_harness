import pytest
from sympy import Symbol

# Test imports sympy directly and uses Symbol from it.
# Compares Symbol('x') with C() and asserts False.
# Handles invalid expressions gracefully without raising AttributeError.

def test_claim_c2():
    # Given: A SymPy Symbol and an object with a repr that evaluates to an invalid expression.
    x = Symbol('x')
    
    class C:
        def __repr__(self):
            return 'x.y'
    
    # When: sympy.Symbol('x') == C()
    # Then: The comparison returns False.
    assert (x == C()) is False
    
    # Edge case: Test with a different invalid expression in C's __repr__ method.
    class D:
        def __repr__(self):
            return 'invalid_expression'
    
    assert (x == D()) is False
    
    # Edge case: Test with a Symbol that has a name different from 'x'.
    y = Symbol('y')
    assert (y == C()) is False
