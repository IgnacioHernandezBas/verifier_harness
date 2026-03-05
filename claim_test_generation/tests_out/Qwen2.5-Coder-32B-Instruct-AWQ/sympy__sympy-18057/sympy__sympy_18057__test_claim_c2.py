import pytest
from sympy import Symbol

# Given: A sympy Symbol 'x' and an object C with __repr__ returning 'x.y'
# When: sympy.Symbol('x').__eq__(C()) is called
# Then: False is returned

class C:
    def __repr__(self):
        return 'x.y'

def test_claim_c2():
    # Create a sympy Symbol 'x'
    x = Symbol('x')
    
    # Create an object C with __repr__ returning 'x.y'
    c = C()
    
    # Test returns False for sympy.Symbol('x') == C()
    assert x == c is False
    
    # Ensure no AttributeError is raised
    with pytest.raises(AttributeError):
        x.y  # This should raise an AttributeError as 'x' is a Symbol and does not have an attribute 'y'
    
    # Verify other edge cases behave as expected
    
    # Comparison with None
    assert x == None is False
    
    # Comparison with a string 'x'
    assert x == 'x' is False
    
    # Comparison with a sympy Symbol 'y'
    y = Symbol('y')
    assert x == y is False
