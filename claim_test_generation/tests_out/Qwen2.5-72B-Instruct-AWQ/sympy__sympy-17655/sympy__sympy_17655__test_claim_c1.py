# Checklist TODO: Test must import Point and Number from sympy.
# Checklist TODO: Test must multiply a scalar by a Point without raising exceptions.
# Checklist TODO: Test must verify the resulting Point has correctly scaled coordinates.
import pytest
from sympy import Point, Number

def test_claim_c1(tmpdir, monkeypatch, capsys):
    # Given: A Point instance and a scalar (sympy.Number)
    point = Point(1, 2)
    scalar = Number(5)

    # When: the scalar is multiplied by the Point (scalar * Point)
    result = scalar * point

    # Then: No exception is raised, and the result is a Point with coordinates scaled by the scalar
    assert isinstance(result, Point), "The result of scalar * Point is a Point."
    assert result == Point(scalar * point[0], scalar * point[1]), "The coordinates of the resulting Point are scaled by the scalar."

    # Edge cases
    # Test with a scalar of 0
    scalar_zero = Number(0)
    result_zero = scalar_zero * point
    assert result_zero == Point(0, 0), "Multiplying by 0 results in a Point with coordinates (0, 0)."

    # Test with a negative scalar
    scalar_negative = Number(-2)
    result_negative = scalar_negative * point
    assert result_negative == Point(scalar_negative * point[0], scalar_negative * point[1]), "The coordinates of the resulting Point are scaled by the negative scalar."

    # Test with a non-integer scalar (e.g., 0.5)
    scalar_non_integer = Number(0.5)
    result_non_integer = scalar_non_integer * point
    assert result_non_integer == Point(scalar_non_integer * point[0], scalar_non_integer * point[1]), "The coordinates of the resulting Point are scaled by the non-integer scalar."
