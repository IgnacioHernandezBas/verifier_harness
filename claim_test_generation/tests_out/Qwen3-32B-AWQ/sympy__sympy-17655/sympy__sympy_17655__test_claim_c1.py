import pytest
from sympy.geometry import Point

def test_claim_c1():
    # Given: Create Point instances with coordinates
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    scalar = 2

    # When: Execute multiplication and addition in both orders
    result1 = (p1 * scalar) + p2
    result2 = p1 + (p2 * scalar)
    result3 = (p1 + p2) * scalar
    result4 = p1 * scalar + p2 * scalar

    # Then: Validate coordinate equality of results
    assert result1 == result2
    assert result3 == result4
    assert result1.x == 5 and result1.y == 8
    assert result3.x == 8 and result3.y == 12

    # Edge case: Test with scalar=0
    assert (p1 * 0) + p2 == p1 + (p2 * 0)
    assert ((p1 + p2) * 0) == p1 * 0 + p2 * 0

    # Edge case: Test with negative scalar (-2)
    assert (p1 * -2) + p2 == p1 + (p2 * -2)
    assert ((p1 + p2) * -2) == p1 * -2 + p2 * -2

    # Edge case: Test non-integer scalar (0.5)
    assert (p1 * 0.5) + p2 == p1 + (p2 * 0.5)
    assert ((p1 + p2) * 0.5) == p1 * 0.5 + p2 * 0.5

    # Edge case: Test Points with different dimensions (Point2D vs Point3D)
    p3 = Point(5, 6, 7)
    p4 = Point(8, 9, 10)
    scalar = 3
    assert (p3 * scalar) + p4 == p3 + (p4 * scalar)
    assert ((p3 + p4) * scalar) == p3 * scalar + p4 * scalar
