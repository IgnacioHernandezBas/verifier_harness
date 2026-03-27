import pytest
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c1(capsys):
    # Given: A tuple containing exactly one element is passed to the code printer
    # When: Calling _recursive_to_string with a single-element tuple argument
    result = _recursive_to_string(True, (1,))

    # Then: The generated code string ends with ',)' syntax (e.g., '(1,)')
    assert result == "(1,)"  # Test passes with single-element tuple input
    assert result.endswith(',)')  # Generated code string ends with ',)' syntax

    # Edge case: Empty tuple input
    result = _recursive_to_string(True, ())
    assert result == "()"  # Test output matches expected string '(,)'

    # Edge case: Multi-element tuple input
    result = _recursive_to_string(True, (1, 2))
    assert result == "(1, 2)"  # Test output matches expected string '(1, 2)'

    # Edge case: Non-tuple input
    with pytest.raises(TypeError):
        _recursive_to_string(True, 1)  # Test fails with incorrect input or parameters

    # Checklist
    # Test passes with single-element tuple input
    # Test fails with incorrect input or parameters
    # Test output matches expected string '(,)'
