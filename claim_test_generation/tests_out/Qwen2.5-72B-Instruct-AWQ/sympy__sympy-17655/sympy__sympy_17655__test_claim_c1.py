# Checklist TODO: Test must verify the claim's behavior.
# Checklist TODO: Test must not rely on internal implementation details.
# Checklist TODO: Test must use the provided data setup and fixtures.
import pytest
from sympy import Point, Point2D, sympify

def test_claim_c1():
    # Given
    point1 = Point(0, 0)
    point2 = Point(1, 1)

    # When
    result1 = point1 + 2 * point2
    result2 = point1 + point2 * 2
    result3 = 2 * point2 + point1

    # Then
    assert result1 == Point2D(2, 2)
    assert result2 == Point2D(2, 2)
    assert result3 == Point2D(2, 2)

    # Edge cases
    # Test with point1 and point2 having different coordinates
    point1_diff = Point(0, 0)
    point2_diff = Point(2, 3)
    result_diff = point1_diff + 2 * point2_diff
    assert result_diff == Point2D(4, 6)

    # Test with a non-integer scalar
    result_non_int = point1 + 2.5 * point2
    assert result_non_int == Point2D(2.5, 2.5)

    # Test with a zero scalar
    result_zero = point1 + 0 * point2
    assert result_zero == Point2D(0, 0)
