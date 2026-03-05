# Checklist TODO: Test must use 'from sympy import Point' for imports.
# Checklist TODO: Test must create a Point object and a scaling factor.
# Checklist TODO: Test must verify the scaled Point's coordinates.
import pytest
from sympy import Point

def test_claim_c2(tmpdir, monkeypatch, capsys):
    # Given: A Point object and a number are provided.
    p = Point(1, 2)
    factor = 3

    # When: sympy.geometry.point.Point.__mul__ is called with a number as the factor.
    scaled_point = p * factor

    # Then: A new Point object is returned.
    assert isinstance(scaled_point, Point)

    # Then: The coordinates of the new Point are scaled by the number.
    assert scaled_point.x == p.x * factor
    assert scaled_point.y == p.y * factor

    # Then: The original Point object remains unchanged.
    assert p.x == 1
    assert p.y == 2

    # Edge cases
    # Test with a scaling factor of 0.
    scaled_point_zero = p * 0
    assert scaled_point_zero.x == 0
    assert scaled_point_zero.y == 0

    # Test with a negative scaling factor.
    scaled_point_negative = p * -2
    assert scaled_point_negative.x == -2
    assert scaled_point_negative.y == -4

    # Test with a non-integer scaling factor.
    scaled_point_non_integer = p * 2.5
    assert scaled_point_non_integer.x == 2.5
    assert scaled_point_non_integer.y == 5.0
