import pytest
from sympy import Symbol

def test_claim_c3():
    # Test imports sympy directly.
    # Create a sympy Symbol 'x'.
    x = Symbol('x')
    
    # Create an object C with __repr__ returning 'x'.
    class C:
        def __repr__(self):
            return 'x'
    
    # Symbol('x').__eq__(C()) returns False.
    assert x.__eq__(C()) is False
    
    # Verify edge cases return expected results.
    # Object C with __repr__ returning a string that does not match the symbol name.
    class C2:
        def __repr__(self):
            return 'y'
    
    assert x.__eq__(C2()) is False
    
    # Object C with __repr__ returning a string that partially matches the symbol name.
    class C3:
        def __repr__(self):
            return 'xy'
    
    assert x.__eq__(C3()) is False
    
    # Object C with __repr__ returning a string that is a substring of the symbol name.
    class C4:
        def __repr__(self):
            return 'x'
    
    assert x.__eq__(C4()) is False
