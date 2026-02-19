import pytest
from sympy import Point

def test_claim_c1(capsys):
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    num = 5

    # When: Multiplying a Point by a number and then adding it to another Point
    result1 = p1 * num + p2

    # Then: Returns the same result as adding the two Points and then multiplying the result by the number
    result2 = (p1 + p2) * num

    # Test passes with two Points and a positive number
    assert result1 == result2

    # Test passes with two Points and a negative number
    num = -5
    result1 = p1 * num + p2
    result2 = (p1 + p2) * num
    assert result1 == result2

    # Test fails with invalid input (e.g. non-numeric multiplier)
    with pytest.raises(TypeError):
        p1 * 'a' + p2

    # Edge cases
    # Multiplying by zero
    num = 0
    result1 = p1 * num + p2
    result2 = (p1 + p2) * num
    assert result1 == result2

    # Adding Points with the same coordinates
    p1 = Point(1, 2)
    p2 = Point(1, 2)
    num = 5
    result1 = p1 * num + p2
    result2 = (p1 + p2) * num
    assert result1 == result2

    # Multiplying by a negative number
    num = -5
    result1 = p1 * num + p2
    result2 = (p1 + p2) * num
    assert result1 == result2
