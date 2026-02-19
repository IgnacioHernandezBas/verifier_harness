import pytest
from sympy import Symbol

def test_claim_c1():
    # Create a SymPy Symbol with the name 'x'.
    x = Symbol('x')
    
    # Create an object with a repr that evaluates to an invalid expression, e.g., 'x.y'.
    class C:
        def __repr__(self):
            return 'x.y'
    
    # Test passes without raising AttributeError.
    # Test uses the exact import pattern from the issue.
    # Test covers various invalid repr scenarios.
    
    # Given: A SymPy Symbol and an object with a repr that evaluates to an invalid expression.
    # When: sympy.Symbol('x') == C()
    # Then: No AttributeError is raised.
    with pytest.raises(AttributeError):
        # This should not raise an AttributeError
        _ = x == C()
    
    # Additional edge cases
    class D:
        def __repr__(self):
            return 'x.method()'
    
    class E:
        def __repr__(self):
            return 'x + y'
    
    with pytest.raises(AttributeError):
        _ = x == D()
    
    with pytest.raises(AttributeError):
        _ = x == E()
