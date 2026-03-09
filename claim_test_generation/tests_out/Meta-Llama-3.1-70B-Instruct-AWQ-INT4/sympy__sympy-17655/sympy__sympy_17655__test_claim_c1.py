import pytest
from sympy import geometry as ge
import sympy

def test_claim_c1(capsys):
    # Given
    point1 = ge.Point(0,0)
    point2 = ge.Point(1,1)

    # When
    result1 = point1 + sympy.sympify(2.0) * point2
    result2 = point1 + point2 * sympy.sympify(2.0)

    # Then
    # returns Point2D(2.0, 2.0)
    assert result1 == ge.Point2D(2.0, 2.0)
    # behaves the same as point1 + point2 * sympy.sympify(2.0)
    assert result1 == result2

    # Test passes with point1 + sympy.sympify(2.0) * point2
    assert result1 == ge.Point2D(2.0, 2.0)

    # Test passes with point1 + point2 * sympy.sympify(2.0)
    assert result2 == ge.Point2D(2.0, 2.0)

    # Test fails with incorrect scalar value or point coordinates
    with pytest.raises(AssertionError):
        assert point1 + sympy.sympify(3.0) * point2 == ge.Point2D(2.0, 2.0)
    with pytest.raises(AssertionError):
        assert point1 + sympy.sympify(2.0) * ge.Point(2,2) == ge.Point2D(2.0, 2.0)
