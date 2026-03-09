import pytest
from sympy.geometry import Point

def test_claim_c2(tmpdir, monkeypatch, capsys):
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    number = 2

    # When: Multiplying a Point by a number and then adding it to another Point
    # Then: Does not raise a TypeError
    try:
        result = (p1 * number) + p2
        assert isinstance(result, Point), "The result of multiplication and addition is a Point"
    except TypeError:
        pytest.fail("Multiplying a Point by a number and then adding it to another Point raised a TypeError")

    # Edge cases
    # Test with a Point and a non-numeric value (e.g., a string)
    with pytest.raises(TypeError):
        p1 * "string"

    # Test with a Point and a complex number
    with pytest.raises(TypeError):
        p1 * (1 + 2j)

    # Test with a Point and a zero value
    try:
        result = (p1 * 0) + p2
        assert isinstance(result, Point), "The result of multiplication by zero and addition is a Point"
    except TypeError:
        pytest.fail("Multiplying a Point by zero and then adding it to another Point raised a TypeError")

    # Checklist
    # Test must import Point from sympy.geometry
    # Test must verify no TypeError is raised during operations
    # Test must cover multiplication and addition of Points
