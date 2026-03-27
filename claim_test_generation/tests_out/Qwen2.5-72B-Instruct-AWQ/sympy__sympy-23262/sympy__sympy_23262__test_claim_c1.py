# Checklist TODO: Test must use a single-element tuple as input.
# Checklist TODO: Test must verify the output string ends with ',)' for the input.
# Checklist TODO: Test must not mock internal/private methods.
import pytest
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c1(monkeypatch):
    # Given: A tuple containing exactly one element is passed to the code printer
    single_element_tuple = (1,)
    
    # Define a mock doprint function that returns a known value
    def mock_doprint(arg):
        return str(arg)
    
    # When: Calling _recursive_to_string with a single-element tuple argument
    monkeypatch.setattr('sympy.utilities.lambdify.doprint', mock_doprint)
    result = _recursive_to_string(mock_doprint, single_element_tuple)
    
    # Then: The generated code string ends with ',)' syntax (e.g., '(1,)')
    assert result.endswith(',)')
    
    # Edge cases
    # Pass an empty tuple to _recursive_to_string
    empty_tuple = ()
    result_empty = _recursive_to_string(mock_doprint, empty_tuple)
    assert result_empty == '()'
    
    # Pass a multi-element tuple to _recursive_to_string
    multi_element_tuple = (1, 2)
    result_multi = _recursive_to_string(mock_doprint, multi_element_tuple)
    assert result_multi == '(1, 2)'
    
    # Pass a non-tuple type to _recursive_to_string
    non_tuple = 1
    result_non_tuple = _recursive_to_string(mock_doprint, non_tuple)
    assert result_non_tuple == '1'
