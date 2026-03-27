# Checklist TODO: Import Point using 'from sympy.geometry import Point'
# Checklist TODO: Construct valid Point objects with numeric coordinates
# Checklist TODO: Verify __add__ completes without exception when combining with scaled Point
import pytest
from sympy.geometry import Point

def test_claim_c3():
    # Given: Construct valid Point objects with numeric coordinates
    point1 = Point(1, 2)
    scaled_point = Point(2, 4)  # Scaled by factor of 2 from (1,2)

    # When: Verify __add__ completes without exception when combining with scaled Point
    result = point1 + scaled_point

    # Then: assert isinstance(point1 + scaled_point, Point)
    assert isinstance(result, Point)
