import pytest
from sympy import Point

def test_claim_c4():
    # Given: A Point object with specific coordinates.
    p1 = Point(1, 2)
    # Given: A scaled Point object by multiplying the original Point with a scalar.
    scaled_p1 = p1 * 3

    # When: sympy.geometry.point.Point.__add__ is called with a scaled Point object.
    result = p1 + scaled_p1

    # Then: A new Point object is returned with the sum of the coordinates.
    assert result == Point(4, 8)

    # Test passes with positive coordinates.
    p2 = Point(3, 4)
    scaled_p2 = p2 * 2
    result2 = p2 + scaled_p2
    assert result2 == Point(9, 12)

    # Test passes with mixed positive and negative coordinates.
    p3 = Point(-1, 2)
    scaled_p3 = p3 * 2
    result3 = p3 + scaled_p3
    assert result3 == Point(-3, 6)

    # Test passes with zero coordinates.
    p4 = Point(0, 0)
    scaled_p4 = p4 * 5
    result4 = p4 + scaled_p4
    assert result4 == Point(0, 0)
