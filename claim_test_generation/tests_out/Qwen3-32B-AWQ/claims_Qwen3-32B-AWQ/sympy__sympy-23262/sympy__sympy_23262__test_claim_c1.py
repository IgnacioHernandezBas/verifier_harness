# Checklist TODO: Test uses public lambdify API, not internal functions
# Checklist TODO: Verifies generated code has trailing comma for single-element tuples
# Checklist TODO: Fails if code printer produces invalid tuple syntax
import pytest
from sympy.utilities.lambdify import lambdify

def test_claim_c1():
    # Given: A single-element tuple as input to lambdify
    # When: Generating code for the tuple via lambdify
    f = lambdify([], (1,))
    result = f()
    # Then: The generated code produces a tuple with trailing comma syntax
    assert result == (1,)
    assert isinstance(result, tuple)
