import pytest

def test_claim_c1():
    # Given: Use package-level imports for Point and Number
    from sympy.geometry import Point
    from sympy import Number
    p = Point(3, 5)
    scalar = Number(2)

    # When: Multiply scalar by Point (scalar * Point)
    result = scalar * p

    # Then: Verify scalar*Point returns new Point with scaled coordinates
    assert result.x == 2 * 3  # 6
    assert result.y == 2 * 5  # 10
    assert isinstance(result, Point)
    # Ensure no TypeError raised during multiplication
