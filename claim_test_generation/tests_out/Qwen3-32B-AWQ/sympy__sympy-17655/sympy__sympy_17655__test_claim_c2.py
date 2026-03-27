# Checklist TODO: Import Point from sympy.geometry
# Checklist TODO: Perform p1 + k*p2 without TypeError
# Checklist TODO: Validate resulting Point coordinates
import pytest
from sympy.geometry import Point

def test_claim_c2():
    # Given: Create two Points and a scalar
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    k = 2

    # When: Multiply Point by scalar and add to another Point
    # Then: No TypeError is raised
    result = p1 + k * p2

    # Then: Verify resulting Point coordinates
    assert result.x == 1 + k * 3  # 1 + 2*3 = 7
    assert result.y == 2 + k * 4  # 2 + 2*4 = 10

    # Edge case: Zero scalar
    result_zero = p1 + 0 * p2
    assert result_zero.x == p1.x
    assert result_zero.y == p1.y

    # Edge case: Negative scalar
    result_neg = p1 + (-1) * p2
    assert result_neg.x == 1 - 3  # 1 + (-1)*3 = -2
    assert result_neg.y == 2 - 4  # 2 + (-1)*4 = -2

    # Edge case: Non-integer coordinates
    p3 = Point(0.5, 1.5)
    result_float = p1 + 2 * p3
    assert result_float.x == 1 + 2 * 0.5  # 1 + 1.0 = 2.0
    assert result_float.y == 2 + 2 * 1.5  # 2 + 3.0 = 5.0
