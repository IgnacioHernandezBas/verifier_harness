# Checklist TODO: Test passes with a single-element tuple.
# Checklist TODO: Test fails with an empty tuple.
# Checklist TODO: Test passes with a multi-element tuple.
import pytest
import inspect
from sympy import lambdify

def test_claim_c1():
    # Given: A tuple with one element is passed to the lambdify function.
    # When: The inspect.getsource(lambdify([], tuple([1]))) function is called.
    # Then: The returned string should include a trailing comma in the return statement.
    source_code = inspect.getsource(lambdify([], tuple([1])))
    assert 'return (1,)' in source_code

    # Test fails with an empty tuple.
    # Given: An empty tuple is passed to the lambdify function.
    # When: The inspect.getsource(lambdify([], tuple([]))) function is called.
    # Then: The returned string should not include a trailing comma in the return statement.
    source_code_empty_tuple = inspect.getsource(lambdify([], tuple([])))
    assert 'return ()' in source_code_empty_tuple

    # Test passes with a multi-element tuple.
    # Given: A tuple with multiple elements is passed to the lambdify function.
    # When: The inspect.getsource(lambdify([], tuple([1, 2, 3]))) function is called.
    # Then: The returned string should not include a trailing comma in the return statement.
    source_code_multi_element_tuple = inspect.getsource(lambdify([], tuple([1, 2, 3])))
    assert 'return (1, 2, 3)' in source_code_multi_element_tuple
