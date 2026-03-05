# Checklist TODO: Test passes without raising exceptions.
# Checklist TODO: Resulting Point is the sum of original and scaled Points.
# Checklist TODO: Test handles edge cases correctly.
import pytest
from sympy import Point

def test_claim_c3():
    # Given: A Point object with specific coordinates.
    p1 = Point(1, 2)
    
    # Given: A scaled Point object by multiplying the original Point by a scalar.
    scaled_p1 = p1 * 3
    
    # When: sympy.geometry.point.Point.__add__ is called with a scaled Point object.
    # Then: No exception is raised.
    result = p1 + scaled_p1
    
    # Test passes without raising exceptions.
    # Resulting Point is the sum of original and scaled Points.
    assert result == Point(4, 8)
    
    # Edge case: Test with a scalar of zero.
    zero_scaled_p1 = p1 * 0
    result_zero = p1 + zero_scaled_p1
    assert result_zero == p1
    
    # Edge case: Test with negative coordinates for the original Point.
    p2 = Point(-1, -2)
    scaled_p2 = p2 * 3
    result_negative = p2 + scaled_p2
    assert result_negative == Point(-4, -6)
    
    # Edge case: Test with non-integer scalar values.
    scaled_p1_non_integer = p1 * 1.5
    result_non_integer = p1 + scaled_p1_non_integer
    assert result_non_integer == Point(2.5, 4.0)
