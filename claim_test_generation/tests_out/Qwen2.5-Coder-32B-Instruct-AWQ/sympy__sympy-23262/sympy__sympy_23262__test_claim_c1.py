# Checklist TODO: Test passes with a single-element tuple.
# Checklist TODO: Lambda function returns a tuple with a single element.
# Checklist TODO: Test handles different types of single-element tuples.
import pytest
from sympy.utilities.lambdify import lambdify

def test_claim_c1():
    # Given: A single-element tuple is provided as the argument to `lambdify`.
    # When: The `lambdify` function is called with an empty list and a single-element tuple.
    f = lambdify([], (1,))
    # Then: The generated lambda function returns a tuple with a single element, represented as (1,).
    assert f() == (1,)

    # Test handles different types of single-element tuples.
    # Given: A single-element tuple with a different integer.
    # When: The `lambdify` function is called with an empty list and a single-element tuple.
    f2 = lambdify([], (2,))
    # Then: The generated lambda function returns a tuple with a single element, represented as (2,).
    assert f2() == (2,)

    # Given: A single-element tuple with a non-integer element.
    # When: The `lambdify` function is called with an empty list and a single-element tuple.
    f3 = lambdify([], ('a',))
    # Then: The generated lambda function returns a tuple with a single element, represented as ('a',).
    assert f3() == ('a',)

    # Test with additional keyword arguments to `lambdify`.
    # Given: A single-element tuple is provided as the argument to `lambdify`.
    # When: The `lambdify` function is called with an empty list, a single-element tuple, and additional keyword arguments.
    f4 = lambdify([], (1,), use_imps=False)
    # Then: The generated lambda function returns a tuple with a single element, represented as (1,).
    assert f4() == (1,)
