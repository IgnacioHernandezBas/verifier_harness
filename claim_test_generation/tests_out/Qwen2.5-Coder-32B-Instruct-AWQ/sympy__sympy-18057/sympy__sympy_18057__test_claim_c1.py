import pytest
from sympy import Symbol

def test_claim_c1():
    # Create a sympy Symbol 'x'
    x = Symbol('x')
    
    # Create an object C with __repr__ returning 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'
    
    # Test passes without raising AttributeError
    # Test uses exact imports as issue's code examples
    assert (x == C()) is False
    
    # Test verifies behavior with non-matching __repr__ strings
    class D:
        def __repr__(self):
            return 'non_matching_string'
    
    assert (x == D()) is False
