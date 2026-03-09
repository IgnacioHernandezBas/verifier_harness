import pytest
from sympy import Point

def test_claim_c3(capsys):
    # GIVEN: A Point object and a scaled Point object are provided.
    p1 = Point(1, 2)
    p2 = Point(3, 4) * 2

    # WHEN: sympy.geometry.point.Point.__add__ is called with a scaled Point object.
    try:
        p1 + p2
    except Exception as e:
        pytest.fail(f"An exception was raised: {e}")

    # THEN: No exception is raised.
    # Test passes without raising a GeometryError
    assert True

    # Test handles different Point dimensions correctly
    p3 = Point(1, 2, 3)
    with pytest.raises(ValueError):
        p1 + p3

    # Test handles invalid inputs correctly
    with pytest.raises(ValueError):
        Point(1, 'a')
