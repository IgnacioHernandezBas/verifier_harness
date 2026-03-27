import pytest
import inspect
from sympy.utilities.lambdify import lambdify

def test_claim_c1():
    # Test confirms single-element tuple generates valid source code.
    # Uses inspect.getsource to capture generated function.
    # Verifies trailing comma ensures tuple recognition.
    # Given
    args = []
    expr = tuple([1])
    # When
    func = lambdify(args, expr)
    source = inspect.getsource(func)
    # Then
    expected = 'def _lambdifygenerated():\n    return (1,)\n'
    assert source == expected
