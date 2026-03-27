# Checklist TODO: Function handles 2+ element tuples with commas
# Checklist TODO: Generated code syntax matches Python standards
# Checklist TODO: Edge cases produce valid tuple representations
import pytest
from sympy.utilities.lambdify import _recursive_to_string
from sympy import symbols, Add

def test_claim_c2():
    # Given: a tuple with two or more elements
    # Define a mock doprint function that converts arguments to strings
    doprint = lambda x: str(x)

    # Test case 1: tuple with integers
    arg = (1, 2)
    # When: calling _recursive_to_string with the tuple
    result = _recursive_to_string(doprint, arg)
    # Then: generated code should be "(1, 2)"
    assert result == "(1, 2)", "Generated code for (1, 2) is incorrect"

    # Test case 2: tuple with SymPy symbols
    x, y = symbols('x y')
    arg = (x, y)
    # When: calling _recursive_to_string with the tuple
    result = _recursive_to_string(doprint, arg)
    # Then: generated code should be "(x, y)"
    assert result == "(x, y)", "Generated code for symbols tuple is incorrect"

    # Test case 3: tuple with mixed elements (int, expression, float)
    expr = Add(x, y)
    arg = (1, expr, 3.14)
    # When: calling _recursive_to_string with the tuple
    result = _recursive_to_string(doprint, arg)
    # Then: generated code should be "(1, x + y, 3.14)"
    assert result == "(1, x + y, 3.14)", "Generated code for mixed tuple is incorrect"

    # Edge case: nested tuples
    arg = ((1, 2), (3, 4))
    # When: calling _recursive_to_string with the nested tuple
    result = _recursive_to_string(doprint, arg)
    # Then: generated code should be "((1, 2), (3, 4))"
    assert result == "((1, 2), (3, 4))", "Generated code for nested tuples is incorrect"
