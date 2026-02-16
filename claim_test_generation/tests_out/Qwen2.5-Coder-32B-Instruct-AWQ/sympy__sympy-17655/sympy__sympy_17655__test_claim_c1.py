# Checklist TODO: Test passes with specified inputs
# Checklist TODO: Both expressions yield the same result
# Checklist TODO: Edge cases are handled without errors
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

    # Both expressions yield the same result
    assert result1 == result2

    # Edge cases: Test with non-numeric values for multiplication
    with pytest.raises(TypeError):
        point1 + point2 * 'a'

    # Edge cases: Test with negative coordinates for points
    point3 = Point(-1, -1)
    point4 = Point(-2, -2)
    result3 = point3 + sympify(2.0) * point4
    assert result3 == Point(-5.0, -5.0)

    # Edge cases: Test with zero coordinates for points
    point5 = Point(0, 0)
    point6 = Point(0, 0)
    result4 = point5 + sympify(2.0) * point6
    assert result4 == Point(0.0, 0.0)
