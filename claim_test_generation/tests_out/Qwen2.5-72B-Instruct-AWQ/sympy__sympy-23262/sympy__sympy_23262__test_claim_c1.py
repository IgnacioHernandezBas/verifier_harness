# Checklist TODO: Test must import lambdify and inspect.
# Checklist TODO: Test must call lambdify with a single-element tuple.
# Checklist TODO: Test must assert the generated function string is correct.
import pytest
from sympy.utilities.lambdify import lambdify
import inspect

def test_claim_c1():
    # GIVEN: A tuple with one element is passed to the lambdify function.
    # WHEN: The inspect.getsource(lambdify([], tuple([1]))) function is called.
    generated_function = lambdify([], tuple([1]))
    generated_source = inspect.getsource(generated_function)
    
    # THEN: The returned string should be 'def _lambdifygenerated():
    #       return (1,)
    expected_source = 'def _lambdifygenerated():\n    return (1,)\n'
    assert generated_source == expected_source, "The generated function does not include a trailing comma for a single-element tuple."
