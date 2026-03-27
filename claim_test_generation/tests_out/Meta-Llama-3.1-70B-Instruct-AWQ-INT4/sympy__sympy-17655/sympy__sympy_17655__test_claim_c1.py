import pytest
from sympy import Point, Number

def test_claim_c1(capsys):
    # Given: A Point instance and a scalar (sympy.Number)
    p = Point(1, 2)
    scalar = Number(5)

    # When: the scalar is multiplied by the Point (scalar * Point)
    result = scalar * p

    # Then: No exception is raised, and the result is a Point with coordinates scaled by the scalar
    assert isinstance(result, Point)  # Test passes without raising an exception
    assert result == Point(5, 10)  # Resulting Point has correct scaled coordinates

    # Edge cases
    # Multiplying by zero
    result = 0 * p
    assert result == Point(0, 0)

    # Multiplying by a negative scalar
    result = -1 * p
    assert result == Point(-1, -2)

    # Multiplying by a non-numeric scalar
    with pytest.raises(TypeError):
        'a' * p

    # Test handles edge cases correctly
    assert True  # This is a placeholder, you can add more assertions here
