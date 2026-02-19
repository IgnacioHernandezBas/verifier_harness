import pytest
from sympy import Point

def test_claim_c2(capsys):
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    num = 5

    # When: Multiplying a Point by a number and then adding it to another Point
    # Then: Does not raise a TypeError
    # Checklist:
    # - Test passes without raising a TypeError
    # - Test correctly handles multiplication and addition of Points
    # - Test covers edge cases and non-standard inputs

    # Assertions:
    # - Multiplying a Point by a number does not raise a TypeError
    # - Adding a Point to another Point does not raise a TypeError
    # - Chaining multiplication and addition of Points does not raise a TypeError

    # Data setup:
    # - Create two Points with different coordinates
    # - Create a number to multiply the Point with
    # - Create another Point to add to the result

    # Edge cases:
    # - Multiplying by zero
    # - Adding two Points with the same coordinates
    # - Multiplying by a non-numeric value

    # Test multiplication by a number
    try:
        result = p1 * num
        assert isinstance(result, Point)
    except TypeError:
        pytest.fail("Multiplying a Point by a number raises a TypeError")

    # Test addition of two Points
    try:
        result = p1 + p2
        assert isinstance(result, Point)
    except TypeError:
        pytest.fail("Adding a Point to another Point raises a TypeError")

    # Test chaining multiplication and addition of Points
    try:
        result = (p1 * num) + p2
        assert isinstance(result, Point)
    except TypeError:
        pytest.fail("Chaining multiplication and addition of Points raises a TypeError")

    # Test edge cases
    # Multiplying by zero
    try:
        result = p1 * 0
        assert isinstance(result, Point)
    except TypeError:
        pytest.fail("Multiplying a Point by zero raises a TypeError")

    # Adding two Points with the same coordinates
    try:
        result = p1 + p1
        assert isinstance(result, Point)
    except TypeError:
        pytest.fail("Adding two Points with the same coordinates raises a TypeError")

    # Multiplying by a non-numeric value
    try:
        result = p1 * 'a'
        pytest.fail("Multiplying a Point by a non-numeric value does not raise a TypeError")
    except TypeError:
        pass

    # Capture output to ensure no unexpected output
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
