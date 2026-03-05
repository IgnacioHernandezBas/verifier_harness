import pytest
from sympy import Point

def test_claim_c2(capsys):
    # Given: A Point object and a number are provided.
    p = Point(1, 2)
    num = 5

    # When: sympy.geometry.point.Point.__mul__ is called with a number as the factor.
    new_p = p * num

    # Then: A new Point object is returned with coordinates scaled by the number.
    # A new Point object is returned
    assert isinstance(new_p, Point)
    # The new Point object has coordinates scaled by the number
    assert new_p == Point(5, 10)

    # Test passes with a positive scaling factor
    assert (p * 5) == Point(5, 10)

    # Test passes with a negative scaling factor
    assert (p * -5) == Point(-5, -10)

    # Test fails with a non-numeric scaling factor
    with pytest.raises(TypeError):
        p * 'a'

    # Scaling by zero
    assert (p * 0) == Point(0, 0)

    # Scaling by a negative number
    assert (p * -5) == Point(-5, -10)

    # Scaling by a non-numeric value
    with pytest.raises(TypeError):
        p * 'a'
