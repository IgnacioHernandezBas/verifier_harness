# Checklist TODO: Test uses public lambdify API
# Checklist TODO: Verifies generated code syntax matches claim
# Checklist TODO: Validates correct runtime behavior of generated function
import pytest
from sympy import lambdify

def test_claim_c1():
    # Given: A tuple containing exactly one element is passed to the code printer
    expr = (1,)

    # When: Generating a lambda function with lambdify
    func = lambdify([], expr)

    # Then: The generated code string ends with ',)' syntax (e.g., '(1,)')
    #       and the resulting lambda function evaluates to a tuple with single element
    result = func()
    assert result == (1,)
    assert isinstance(result, tuple)
