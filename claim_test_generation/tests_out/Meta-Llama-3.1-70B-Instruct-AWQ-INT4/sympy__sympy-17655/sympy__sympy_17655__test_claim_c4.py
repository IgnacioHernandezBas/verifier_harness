import pytest
from sympy import Point

def test_claim_c4(capsys):
    # Given: A Point object and a scaled Point object are provided.
    p1 = Point(1, 2)
    p2 = Point(3, 4)

    # When: sympy.geometry.point.Point.__add__ is called with a scaled Point object.
    p3 = p1 + p2

    # Then: A new Point object is returned with the sum of the coordinates.
    assert isinstance(p3, Point)  # A new Point object is returned
    assert p3 == Point(4, 6)  # The new Point object has the sum of the coordinates

    # Checklist
    # Test passes with valid Point objects
    assert p3 == Point(4, 6)

    # Test raises TypeError with invalid input
    with pytest.raises(TypeError):
        p1 + "invalid input"

    # Test returns correct result with scaled Point object
    p4 = Point(2, 3) * 2
    p5 = p1 + p4
    assert p5 == Point(4, 7)

    # Edge cases
    # Passing a non-Point object to __add__
    with pytest.raises(TypeError):
        p1 + "non-Point object"

    # Passing a Point object with different dimensions
    p6 = Point(1, 2, 3)
    with pytest.raises(ValueError):
        p1 + p6

    # Passing a scaled Point object with zero scale factor
    p7 = Point(2, 3) * 0
    p8 = p1 + p7
    assert p8 == p1
