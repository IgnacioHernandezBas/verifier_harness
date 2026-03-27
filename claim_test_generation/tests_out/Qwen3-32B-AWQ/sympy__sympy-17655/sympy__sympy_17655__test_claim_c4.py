# Checklist TODO: Uses from sympy.geometry import Point
# Checklist TODO: Verifies coordinate summation after addition
# Checklist TODO: Confirms new Point instance is returned
import pytest
from sympy.geometry import Point

def test_claim_c4():
    # Given: Create base Point(1, 2) and scaled Point(3*2, 4*2)
    base_point = Point(1, 2)
    scaled_point = Point(3, 4) * 2  # Scaled Point(6, 8)
    
    # When: Perform addition
    result = base_point + scaled_point  # Point(1+6, 2+8)
    
    # Then: Verify coordinate summation and new instance
    assert result.x == 7  # 1 + 6
    assert result.y == 10  # 2 + 8
    assert isinstance(result, Point)
    assert result is not base_point

    # Edge case: Addition with zero-scaled Point (0,0)
    zero_scaled = Point(0, 0) * 0
    assert (base_point + zero_scaled) == base_point

    # Edge case: Negative scaling
    neg_scaled = Point(-3, -4) * 2  # Point(-6, -8)
    assert (base_point + neg_scaled).x == 1 + (-6)  # -5
    assert (base_point + neg_scaled).y == 2 + (-8)  # -6
