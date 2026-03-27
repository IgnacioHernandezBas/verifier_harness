# Checklist TODO: Test passes without throwing an exception
# Checklist TODO: Test returns False when comparing sympy.Symbol('x') and C()
# Checklist TODO: Test handles edge cases correctly
import pytest
import sympy

# Given: A custom class C with __repr__ returning 'x'
class C:
    def __repr__(self):
        return 'x'

# When: Calling __eq__ between sympy.Symbol('x') and C()
def test_claim_c2(capsys):
    # Create a sympy.Symbol('x')
    x = sympy.Symbol('x')
    
    # Create an instance of the custom class C
    c = C()
    
    # Call __eq__ between sympy.Symbol('x') and C()
    result = x == c
    
    # Then: Returns False
    assert result is False
    
    # Test passes without throwing an exception
    assert not capsys.readouterr().err
    
    # Test handles edge cases correctly
    # Compare sympy.Symbol('x') and C() with different __repr__ values
    class D:
        def __repr__(self):
            return 'y'
    d = D()
    assert x != d
    
    # Compare sympy.Symbol('x') and C() with different symbol names
    y = sympy.Symbol('y')
    assert x != y
    
    # Compare sympy.Symbol('x') and C() with different types
    assert x != 1
