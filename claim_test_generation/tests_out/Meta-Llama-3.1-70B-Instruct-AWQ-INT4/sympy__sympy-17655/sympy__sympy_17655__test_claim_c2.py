import pytest
from sympy import Point

def test_claim_c2(capsys):
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    num = 5

    # When: Multiplying a Point by a number and then adding it to another Point
    # Then: Does not raise a TypeError
    # Checklist: Test passes without raising a TypeError
    try:
        result = p1 * num + p2
    except TypeError:
        pytest.fail("Multiplying a Point by a number and then adding it to another Point raised a TypeError")

    # Assertions
    # Multiplying a Point by a number does not raise a TypeError
    assert isinstance(p1 * num, Point)
    # Adding a Point to another Point does not raise a TypeError
    assert isinstance(p1 + p2, Point)
    # Chaining multiplication and addition of Points does not raise a TypeError
    assert isinstance(result, Point)

    # Edge cases
    # Multiplying by zero
    assert isinstance(p1 * 0, Point)
    # Adding two Points with the same coordinates
    assert isinstance(p1 + p1, Point)
    # Multiplying by a non-numeric value
    with pytest.raises(TypeError):
        p1 * "a"

    # Checklist
    # Test correctly handles multiplication and addition of Points
    assert isinstance(p1 * num, Point)
    assert isinstance(p1 + p2, Point)
    # Test covers edge cases and non-standard inputs
    assert isinstance(p1 * 0, Point)
    assert isinstance(p1 + p1, Point)
    with pytest.raises(TypeError):
        p1 * "a"
