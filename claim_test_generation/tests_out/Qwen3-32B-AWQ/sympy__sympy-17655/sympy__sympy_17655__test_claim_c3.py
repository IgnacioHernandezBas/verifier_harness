# Checklist TODO: Use 'from sympy.geometry import Point' for correct imports
# Checklist TODO: Verify addition returns new Point without GeometryError
# Checklist TODO: Test both 2D and 3D Point additions in separate cases
import pytest
from sympy.geometry import Point

def test_claim_c3():
    # Given: Create base Point and scaled Point
    p1 = Point(0, 0)
    p2 = Point(2, 2)  # Scaled by 2 from p1

    # When: Add the two Points
    result = p1 + p2

    # Then: No exception raised and result is correct
    assert result == Point(2, 2)
