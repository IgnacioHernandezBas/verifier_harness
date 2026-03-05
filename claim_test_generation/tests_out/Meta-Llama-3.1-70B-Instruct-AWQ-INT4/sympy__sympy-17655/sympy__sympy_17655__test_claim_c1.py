import pytest
from sympy import Point

def test_claim_c1(capsys):
    # Given: A Point object and a number are provided.
    p = Point(1, 2)
    num = 5

    # When: sympy.geometry.point.Point.__mul__ is called with a number as the factor.
    # Then: No exception is raised.
    # Test passes without raising a GeometryError
    assert p * num == Point(5, 10)

    # Test handles edge cases correctly
    # Multiplying by zero
    assert p * 0 == Point(0, 0)

    # Multiplying by a negative number
    assert p * -1 == Point(-1, -2)

    # Multiplying by a non-numeric value
    with pytest.raises(TypeError):
        p * 'a'

    # Test uses correct imports and module
    assert isinstance(p, Point)

    # Capture stdout and stderr
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''
