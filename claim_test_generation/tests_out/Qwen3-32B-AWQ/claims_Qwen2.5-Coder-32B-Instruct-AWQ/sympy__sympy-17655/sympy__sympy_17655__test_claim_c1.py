# Checklist TODO: Test verifies point arithmetic with scalar produces correct coordinates
# Checklist TODO: Confirms commutative operation equivalence (a + b vs b + a)
# Checklist TODO: Validates result is a Point with numeric coordinates
import pytest
from sympy import Point, sympify

def test_claim_c1():
    # Given: Create points and scalar
    point1 = Point(0, 0)
    point2 = Point(1, 1)
    scalar = sympify(2.0)

    # When: Perform both arithmetic expressions
    result1 = point1 + scalar * point2
    result2 = point1 + point2 * scalar

    # Then: Validate results match expected Point and properties
    assert result1 == Point(2.0, 2.0)
    assert result2 == Point(2.0, 2.0)
    assert result1 == result2
    assert all(isinstance(c, type(sympify(1.0))) for c in (result1.x, result1.y))
