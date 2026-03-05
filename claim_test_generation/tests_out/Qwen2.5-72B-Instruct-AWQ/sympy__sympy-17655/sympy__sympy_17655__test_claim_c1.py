# Checklist TODO: Test must use 'from sympy import Point' for imports.
# Checklist TODO: Test must create Points and a number directly in the test function.
# Checklist TODO: Test must verify the distributive property of Point multiplication and addition.
import pytest
from sympy import Point

def test_claim_c1():
    # Given: Two Points and a number
    p1 = Point(1, 2)
    p2 = Point(3, 4)
    num = 5

    # When: Multiplying a Point by a number and then adding it to another Point
    result1 = p1 * num + p2

    # Then: Returns the same result as adding the two Points and then multiplying the result by the number
    result2 = (p1 + p2) * num
    assert result1 == result2

    # Edge cases
    # Test with a zero multiplier
    num_zero = 0
    result1_zero = p1 * num_zero + p2
    result2_zero = (p1 + p2) * num_zero
    assert result1_zero == result2_zero

    # Test with negative coordinates
    p3 = Point(-1, -2)
    p4 = Point(-3, -4)
    result1_neg = p3 * num + p4
    result2_neg = (p3 + p4) * num
    assert result1_neg == result2_neg

    # Test with a multiplier of 1
    num_one = 1
    result1_one = p1 * num_one + p2
    result2_one = (p1 + p2) * num_one
    assert result1_one == result2_one
