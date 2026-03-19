# Checklist TODO: Use from sympy import Point, Number
# Checklist TODO: Verify scalar*Point returns scaled Point
# Checklist TODO: Confirm no TypeError raised during operation
import pytest
from sympy.geometry import Point
from sympy import Number

def test_claim_c1():
    # Given: Create Point(1, 2) instance and scalar Number(3)
    p = Point(1, 2)
    scalar = Number(3)
    # When: Multiply scalar by Point
    result = scalar * p
    # Then: Check result is Point with scaled coordinates
    assert isinstance(result, Point)
    assert result.x == scalar * p.x
    assert result.y == scalar * p.y

    # Edge case: Zero scalar
    zero_scalar = Number(0)
    zero_result = zero_scalar * p
    assert isinstance(zero_result, Point)
    assert zero_result.x == 0
    assert zero_result.y == 0

    # Negative case: Point(-1, 0)
    p_neg = Point(-1, 0)
    result_neg = scalar * p_neg
    assert isinstance(result_neg, Point)
    assert result_neg.x == -3
    assert result_neg.y == 0
