# Checklist TODO: Test passes with positive coordinates.
# Checklist TODO: Test passes with negative coordinates.
# Checklist TODO: Test handles multiplication by zero correctly.
import pytest
from sympy.geometry import Point

def test_claim_c1():
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    number = 2

    # When: Multiplying a Point by a number and then adding it to another Point
    result1 = p1 * number + p2

    # Then: Returns the same result as adding the two Points and then multiplying the result by the number
    result2 = (p1 + p2) * number
    assert result1 == result2

    # Test passes with positive coordinates
    p1 = Point(5, 6)
    p2 = Point(7, 8)
    number = 3
    result1 = p1 * number + p2
    result2 = (p1 + p2) * number
    assert result1 == result2

    # Test passes with negative coordinates
    p1 = Point(-1, -2)
    p2 = Point(-3, -4)
    number = 2
    result1 = p1 * number + p2
    result2 = (p1 + p2) * number
    assert result1 == result2

    # Test handles multiplication by zero correctly
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    number = 0
    result1 = p1 * number + p2
    result2 = (p1 + p2) * number
    assert result1 == result2

    # Test handles multiplication by one correctly
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    number = 1
    result1 = p1 * number + p2
    result2 = (p1 + p2) * number
    assert result1 == result2
