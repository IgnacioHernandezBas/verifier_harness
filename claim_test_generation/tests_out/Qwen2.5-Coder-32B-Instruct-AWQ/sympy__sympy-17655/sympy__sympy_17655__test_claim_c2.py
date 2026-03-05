import pytest
from sympy import Point

def test_claim_c2():
    # Given: A Point object with specific coordinates.
    p = Point(1, 2)
    # Given: Choose a number to multiply the Point by.
    factor = 3

    # When: sympy.geometry.point.Point.__mul__ is called with a number as the factor.
    result = p * factor

    # Then: A new Point object is returned with coordinates scaled by the number.
    assert isinstance(result, Point)
    assert result.x == 3
    assert result.y == 6

    # Test multiplies Point by a positive integer correctly.
    assert (p * 4).x == 4
    assert (p * 4).y == 8

    # Test multiplies Point by zero results in origin.
    assert (p * 0).x == 0
    assert (p * 0).y == 0

    # Test multiplies Point by a negative number inverts coordinates.
    assert (p * -1).x == -1
    assert (p * -1).y == -2

    # Test multiplies Point by a float should scale the coordinates proportionally.
    assert (p * 0.5).x == 0.5
    assert (p * 0.5).y == 1.0
