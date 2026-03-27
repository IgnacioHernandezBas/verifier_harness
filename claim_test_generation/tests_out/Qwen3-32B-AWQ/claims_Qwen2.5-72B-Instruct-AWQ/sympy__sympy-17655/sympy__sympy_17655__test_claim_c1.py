# Checklist TODO: Test multiplies Point by number without exception
# Checklist TODO: Verifies coordinate scaling matches factor
# Checklist TODO: Confirms no GeometryError raised for valid inputs
import pytest
from sympy.geometry.point import Point

@pytest.mark.parametrize("coords, factor, expected_coords", [
    # Basic multiplication
    ((1, 2), 3, (3, 6)),
    # Negative scaling
    ((-3, 4), 0.5, (-1.5, 2.0)),
    # Zero multiplication
    ((0, 0), -1, (0, 0)),
    # Zero factor
    ((2, 3), 0, (0, 0)),
    # Negative to positive
    ((-5, -5), -1, (5, 5)),
    # Float factor
    ((1.5, 2.5), 2.0, (3.0, 5.0)),
    # Large number scaling
    ((1000000, 2000000), 1e6, (1e12, 2e12)),
])
def test_claim_c1(coords, factor, expected_coords):
    # Given: Create Point instance
    p = Point(*coords)
    
    # When: Multiply by factor
    result = p * factor
    
    # Then: Verify no exception and correct result
    expected = Point(*expected_coords)
    assert isinstance(result, Point)
    assert result == expected
