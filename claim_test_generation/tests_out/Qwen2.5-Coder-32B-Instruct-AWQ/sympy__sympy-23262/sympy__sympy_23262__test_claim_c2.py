# Checklist TODO: Test confirms tuple return with multiple elements.
# Checklist TODO: Handles tuples of varying lengths correctly.
# Checklist TODO: Generates code with commas between tuple elements.
import pytest
from sympy import lambdify
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c2():
    # Given: A tuple with two or more elements is passed to lambdify.
    # When: Calling lambdify with a tuple of two or more elements.
    # Then: The generated code should return a tuple with commas between elements.

    # Test confirms tuple return with multiple elements.
    f1 = lambdify([], (1, 2))
    assert isinstance(f1(), tuple)  # Result is a tuple.
    assert f1() == (1, 2)  # Generated function returns a tuple with commas.

    # Handles tuples of varying lengths correctly.
    f2 = lambdify([], (1, 2, 3))
    assert isinstance(f2(), tuple)  # Result is a tuple.
    assert f2() == (1, 2, 3)  # Generated function returns a tuple with commas.

    # Uses different data types within the tuple elements.
    f3 = lambdify([], (1, 'a', 3.0))
    assert isinstance(f3(), tuple)  # Result is a tuple.
    assert f3() == (1, 'a', 3.0)  # Generated function returns a tuple with commas.

    # Edge case: Pass an empty tuple to lambdify.
    f4 = lambdify([], ())
    assert isinstance(f4(), tuple)  # Result is a tuple.
    assert f4() == ()  # Generated function returns an empty tuple.

    # Edge case: Pass a tuple with a single element to lambdify.
    f5 = lambdify([], (1,))
    assert isinstance(f5(), tuple)  # Result is a tuple.
    assert f5() == (1,)  # Generated function returns a tuple with a trailing comma.

    # Edge case: Pass a tuple with nested tuples to lambdify.
    f6 = lambdify([], ((1, 2), (3, 4)))
    assert isinstance(f6(), tuple)  # Result is a tuple.
    assert f6() == ((1, 2), (3, 4))  # Generated function returns a tuple with nested tuples.

    # Check _recursive_to_string directly
    doprint = lambda x: x
    assert _recursive_to_string(doprint, (1, 2)) == '(1, 2)'
    assert _recursive_to_string(doprint, (1, 'a', 3.0)) == "(1, 'a', 3.0)"
    assert _recursive_to_string(doprint, ()) == '()'
    assert _recursive_to_string(doprint, (1,)) == '(1,)'
    assert _recursive_to_string(doprint, ((1, 2), (3, 4))) == '((1, 2), (3, 4))'
