# Checklist TODO: Test verifies the correct result of point1 + sympy.sympify(2.0) * point2
# Checklist TODO: Test verifies the correct result of point1 + point2 * sympy.sympify(2.0)
# Checklist TODO: Test handles various coordinate types for point1 and point2
import pytest
from sympy import sympify
from sympy.geometry.point import Point

def test_claim_c1():
    # Given: point1 is a Point object with coordinates (0,0) and point2 is a Point object with coordinates (1,1)
    point1 = Point(0, 0)
    point2 = Point(1, 1)

    # When: point1 + sympy.sympify(2.0) * point2
    result1 = point1 + sympify(2.0) * point2

    # Then: returns Point2D(2.0, 2.0)
    assert result1 == Point(2.0, 2.0)

    # When: point1 + point2 * sympy.sympify(2.0)
    result2 = point1 + point2 * sympify(2.0)

    # Then: returns Point2D(2.0, 2.0)
    assert result2 == Point(2.0, 2.0)

    # Test with point1 and point2 having integer coordinates
    point1_int = Point(0, 0)
    point2_int = Point(1, 1)
    assert point1_int + sympify(2) * point2_int == Point(2, 2)
    assert point1_int + point2_int * sympify(2) == Point(2, 2)

    # Test with point1 and point2 having negative coordinates
    point1_neg = Point(-1, -1)
    point2_neg = Point(-1, -1)
    assert point1_neg + sympify(2.0) * point2_neg == Point(-3.0, -3.0)
    assert point1_neg + point2_neg * sympify(2.0) == Point(-3.0, -3.0)

    # Test with point1 and point2 having zero coordinates
    point1_zero = Point(0, 0)
    point2_zero = Point(0, 0)
    assert point1_zero + sympify(2.0) * point2_zero == Point(0.0, 0.0)
    assert point1_zero + point2_zero * sympify(2.0) == Point(0.0, 0.0)
