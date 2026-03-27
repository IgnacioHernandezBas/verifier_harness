import pytest
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c1():
    # Given: A tuple containing exactly one element is passed to the code printer
    # When: Calling _recursive_to_string with a single-element tuple argument
    # Then: The generated code string ends with ',)' syntax (e.g., '(1,)')

    # Create a single-element tuple as input
    int_tuple = (1,)
    str_tuple = ("hello",)
    none_tuple = (None,)

    # Prepare a mock doprint function that returns its argument as a string
    def mock_doprint(arg):
        return str(arg)

    # Test passes with a single-element integer tuple
    result_int = _recursive_to_string(mock_doprint, int_tuple)
    assert result_int.endswith(',)')

    # Test passes with a single-element string tuple
    result_str = _recursive_to_string(mock_doprint, str_tuple)
    assert result_str.endswith(',)')

    # Test handles None in the tuple correctly
    result_none = _recursive_to_string(mock_doprint, none_tuple)
    assert result_none.endswith(',)')
