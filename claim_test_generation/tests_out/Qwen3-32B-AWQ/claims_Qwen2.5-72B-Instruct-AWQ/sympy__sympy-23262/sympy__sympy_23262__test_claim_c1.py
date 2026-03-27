# Checklist TODO: lambdify produces lambda returning single-element tuple
# Checklist TODO: Lambda invocation preserves tuple structure
# Checklist TODO: Output matches (1,) exactly
import pytest
from sympy.utilities.lambdify import lambdify

def test_claim_c1():
    # Given: empty list and single-element tuple
    args = []
    expr = (1,)
    
    # When: generate lambda function
    func = lambdify(args, expr)
    
    # Then: check the output
    result = func()
    assert result == (1,)  # Output matches (1,) exactly
    assert isinstance(result, tuple)  # Result is a tuple
    assert len(result) == 1  # Tuple has single element
    assert "tuple" in str(type(result))  # Type string contains "tuple"
