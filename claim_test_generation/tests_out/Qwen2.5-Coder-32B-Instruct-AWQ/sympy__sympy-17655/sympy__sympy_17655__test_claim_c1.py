# Checklist TODO: Test passes with specified points and multiplication.
# Checklist TODO: Test confirms commutative property of addition and multiplication.
# Checklist TODO: Edge cases handle errors gracefully.
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

    # Edge case: Multiplication by zero (point1 + sympy.sympify(0.0) * point2)
    result3 = point1 + sympify(0.0) * point2
    assert result3 == Point(0.0, 0.0)

    # Edge case: Addition with a non-Point object (point1 + sympy.sympify(2.0))
    with pytest.raises(TypeError):
        _ = point1 + sympify(2.0)

    # Edge case: Multiplication with a non-numeric object (point1 + point2 * 'string')
    with pytest.raises(TypeError):
        _ = point1 + point2 * 'string'
