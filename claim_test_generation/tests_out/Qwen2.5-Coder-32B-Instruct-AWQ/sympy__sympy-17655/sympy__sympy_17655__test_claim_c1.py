import pytest
from sympy import Point, Number

def test_claim_c1():
    # Create a Point instance with specific coordinates.
    p = Point(1, 2)
    
    # Define a scalar using sympy.Number.
    scalar = Number(3)
    
    # Verify no exceptions occur during scalar multiplication.
    # Check resulting Point coordinates are correctly scaled.
    result = scalar * p
    assert isinstance(result, Point)
    assert result.x == 3
    assert result.y == 6
    
    # Test multiplication with a scalar of value zero.
    zero_scalar = Number(0)
    zero_result = zero_scalar * p
    assert isinstance(zero_result, Point)
    assert zero_result.x == 0
    assert zero_result.y == 0
    
    # Test multiplication with a negative scalar.
    negative_scalar = Number(-2)
    negative_result = negative_scalar * p
    assert isinstance(negative_result, Point)
    assert negative_result.x == -2
    assert negative_result.y == -4
    
    # Test multiplication with a non-integer scalar.
    non_integer_scalar = Number(1.5)
    non_integer_result = non_integer_scalar * p
    assert isinstance(non_integer_result, Point)
    assert non_integer_result.x == 1.5
    assert non_integer_result.y == 3.0
    
    # Ensure test covers various scalar types and values.
    # (Already covered by the previous tests)
