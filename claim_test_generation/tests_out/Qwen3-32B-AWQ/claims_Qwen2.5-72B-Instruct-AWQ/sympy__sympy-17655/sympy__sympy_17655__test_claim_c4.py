# Checklist TODO: Test adds Point and scaled Point correctly
# Checklist TODO: Verifies coordinate summation in result
# Checklist TODO: Confirms return type is new Point instance
import pytest
from sympy.geometry import Point
from sympy import symbols

def test_claim_c4():
    # Given: base Point and scaled Point
    p1 = Point(1, 2)
    scaled_p1 = 2 * p1  # Point(2, 4)
    
    # When: add them
    result = p1 + scaled_p1
    
    # Then: new Point with summed coordinates
    assert isinstance(result, Point)
    assert result.x == 3
    assert result.y == 6
    # Original points remain unmodified
    assert p1.x == 1 and p1.y == 2
    assert scaled_p1.x == 2 and scaled_p1.y == 4

    # Additional test case: Point(3,4) + 1.5*Point(2,2)
    p2 = Point(3, 4)
    scaled_p2 = 1.5 * Point(2, 2)  # Point(3, 3)
    result2 = p2 + scaled_p2
    assert result2.x == 6
    assert result2.y == 7

    # Edge case: zero-scaled Point
    zero_scaled = 0 * Point(1, 1)
    result_zero = Point(0, 0) + zero_scaled
    assert result_zero.x == 0
    assert result_zero.y == 0

    # Symbolic scale factor
    a = symbols('a')
    sym_scaled = a * Point(1, 1)
    result_sym = Point(0, 0) + sym_scaled
    assert result_sym.x == a
    assert result_sym.y == a

    # Negative scaling
    neg_scaled = -1 * Point(2, 3)
    result_neg = Point(5, 5) + neg_scaled
    assert result_neg.x == 3
    assert result_neg.y == 2
