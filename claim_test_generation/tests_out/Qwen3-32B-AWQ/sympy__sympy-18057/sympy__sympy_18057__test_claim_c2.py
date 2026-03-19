# Checklist TODO: Symbol 'x' does not equal C instance with __repr__ 'x'
# Checklist TODO: Equality check returns False for mismatched types
# Checklist TODO: Custom __repr__ doesn't override SymPy equality logic
import pytest
import sympy

def test_claim_c2():
    # Given: A custom class C with __repr__ returning 'x'
    class C:
        def __repr__(self):
            return 'x'
    
    # When: Calling __eq__ between sympy.Symbol('x') and C()
    x = sympy.Symbol('x')
    c = C()
    result = x == c
    
    # Then: Returns False
    assert result is False
    assert isinstance(result, bool)
    assert result is not True
