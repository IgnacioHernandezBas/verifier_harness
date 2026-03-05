# Checklist TODO: Test multiplies Point by a positive integer without error
# Checklist TODO: Test multiplies Point by zero without error
# Checklist TODO: Test multiplies Point by a negative number without error
import pytest
from sympy import Point

def test_claim_c1():
    # Given: A Point object with specific coordinates
    p = Point(1, 2)
    
    # Given: Define a number to multiply the Point by
    number = 3
    
    # When: sympy.geometry.point.Point.__mul__ is called with a number as the factor
    # Then: No exception is raised when multiplying a Point by a positive integer
    result = p * number
    assert isinstance(result, Point)
    
    # When: sympy.geometry.point.Point.__mul__ is called with zero as the factor
    # Then: No exception is raised when multiplying a Point by zero
    result_zero = p * 0
    assert isinstance(result_zero, Point)
    
    # When: sympy.geometry.point.Point.__mul__ is called with a negative number as the factor
    # Then: No exception is raised when multiplying a Point by a negative number
    result_negative = p * -2
    assert isinstance(result_negative, Point)
