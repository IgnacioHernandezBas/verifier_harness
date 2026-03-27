# Checklist TODO: Verify single-element tuple gets comma in generated code
# Checklist TODO: Confirm function handles tuple argument correctly
# Checklist TODO: Validate output format matches Python syntax requirements
import pytest
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c1():
    # Given: A tuple with one element is passed to lambdify
    doprint = lambda x: str(x)
    arg = (1,)
    
    # When: Calling _recursive_to_string with the tuple
    result = _recursive_to_string(doprint, arg)
    
    # Then: The generated code should return a tuple with a comma after the element
    assert result == '(1,)'
