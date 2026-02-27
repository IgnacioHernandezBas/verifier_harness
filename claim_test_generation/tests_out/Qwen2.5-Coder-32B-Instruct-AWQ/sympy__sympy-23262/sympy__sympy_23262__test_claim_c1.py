# Checklist TODO: Test confirms tuple with one element includes trailing comma.
# Checklist TODO: Test handles empty tuple correctly.
# Checklist TODO: Test verifies multiple element tuples are formatted correctly.
import pytest
from sympy import lambdify
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c1(monkeypatch):
    # Given: A tuple with one element is passed to lambdify.
    # When: Calling lambdify with a tuple of one element.
    f1 = lambdify([], (1,))
    result = f1()
    
    # Then: The generated code should return a tuple with a comma after the element.
    assert isinstance(result, tuple)  # Result is a tuple with trailing comma.
    assert len(result) == 1  # Tuple has one element.
    assert result == (1,)  # Tuple contains the correct element with trailing comma.

    # Test handles empty tuple correctly.
    f2 = lambdify([], ())
    result = f2()
    assert isinstance(result, tuple)  # Result is a tuple.
    assert len(result) == 0  # Tuple is empty.

    # Test verifies multiple element tuples are formatted correctly.
    f3 = lambdify([], (1, 2, 3))
    result = f3()
    assert isinstance(result, tuple)  # Result is a tuple.
    assert len(result) == 3  # Tuple has three elements.
    assert result == (1, 2, 3)  # Tuple contains the correct elements.

    # Additional check for _recursive_to_string
    def mock_doprint(arg):
        return str(arg)
    
    monkeypatch.setattr('sympy.utilities.lambdify.doprint', mock_doprint)
    result = _recursive_to_string(mock_doprint, (1,))
    assert result == "(1,)"  # _recursive_to_string returns string with trailing comma.
