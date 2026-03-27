# Checklist TODO: Test uses 'from sympy import Symbol' import pattern
# Checklist TODO: Comparison returns False for non-Symbol objects
# Checklist TODO: No AttributeError raised during comparison
import pytest
from sympy import Symbol

def test_claim_c2():
    # Given: A sympy Symbol 'x' and an object C with __repr__ returning 'x.y'
    x = Symbol('x')
    class C:
        def __repr__(self):
            return 'x.y'
    
    # When: sympy.Symbol('x').__eq__(C()) is called
    result = x.__eq__(C())
    
    # Then: False is returned
    assert result is False
