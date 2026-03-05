# Checklist TODO: Test must import sympy and use it to create Point objects.
# Checklist TODO: Test must call the __add__ method and verify the result.
# Checklist TODO: Test must cover edge cases including zero, negative, and large coordinates.
import pytest
from sympy import Point

def test_claim_c4(tmpdir, monkeypatch, capsys):
    # GIVEN: Create a Point object with coordinates (1, 2).
    point1 = Point(1, 2)
    
    # GIVEN: Create a scaled Point object with coordinates (3, 4).
    point2 = Point(3, 4)
    
    # WHEN: Call the __add__ method on the first Point with the second Point as an argument.
    result = point1 + point2
    
    # THEN: A new Point object is returned with the sum of the coordinates.
    assert result == Point(4, 6)
    
    # THEN: The coordinates of the new Point are the sum of the original and scaled Point.
    assert result.x == point1.x + point2.x
    assert result.y == point1.y + point2.y
    
    # THEN: The original and scaled Points are not modified.
    assert point1 == Point(1, 2)
    assert point2 == Point(3, 4)
    
    # EDGE CASE: Test with a Point and a scaled Point with zero coordinates.
    point_zero = Point(0, 0)
    result_zero = point1 + point_zero
    assert result_zero == Point(1, 2)
    
    # EDGE CASE: Test with a Point and a scaled Point with negative coordinates.
    point_negative = Point(-1, -2)
    result_negative = point1 + point_negative
    assert result_negative == Point(0, 0)
    
    # EDGE CASE: Test with a Point and a scaled Point with very large coordinates.
    point_large = Point(1000000, 1000000)
    result_large = point1 + point_large
    assert result_large == Point(1000001, 1000002)
