import pytest
from sympy.geometry import Point

def test_claim_c2():
    # Create Point instance with explicit coordinates
    original_point = Point(2, 3)
    scalar = 2
    # Multiply by scalar using __mul__ operator
    new_point = original_point * scalar
    # Validate scaled coordinates in resulting Point
    assert new_point.x == original_point.x * scalar
    assert new_point.y == original_point.y * scalar
    assert isinstance(new_point, Point)

    # Edge case: Multiply by zero (0)
    scalar = 0
    new_point = original_point * scalar
    assert new_point.x == 0
    assert new_point.y == 0
    assert isinstance(new_point, Point)

    # Edge case: Multiply by negative number (-1.5)
    scalar = -1.5
    new_point = original_point * scalar
    assert new_point.x == original_point.x * scalar
    assert new_point.y == original_point.y * scalar
    assert isinstance(new_point, Point)

    # Edge case: Multiply by non-integer (2.5)
    scalar = 2.5
    new_point = original_point * scalar
    assert new_point.x == original_point.x * scalar
    assert new_point.y == original_point.y * scalar
    assert isinstance(new_point, Point)
