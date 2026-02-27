import pytest
from sympy.geometry import Point

def test_claim_c2():
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    number = 2

    # When: Multiplying a Point by a number and adding it to another Point
    # Then: Does not raise a TypeError
    result = p1 * number + p2

    # Test passes without raising TypeError
    assert isinstance(result, Point)

    # Works with negative coordinates
    p3 = Point(-1, -2)
    p4 = Point(-3, -4)
    result_negative = p3 * number + p4
    assert isinstance(result_negative, Point)

    # Handles multiplication by zero
    result_zero = p1 * 0 + p2
    assert isinstance(result_zero, Point)
