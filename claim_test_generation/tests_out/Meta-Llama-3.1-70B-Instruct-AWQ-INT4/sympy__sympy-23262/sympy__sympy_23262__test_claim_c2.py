import pytest
from sympy import lambdify
from sympy.utilities.lambdify import _recursive_to_string

def test_claim_c2(capsys):
    # | GIVEN: A tuple with two or more elements is passed to lambdify.
    # | WHEN: Calling lambdify with a tuple of two or more elements.
    # | THEN: The generated code should return a tuple with commas between elements.

    # Test passes with a tuple of two or more elements
    # Create a tuple with two or more elements
    tup = (1, 2, 3)
    # Pass the tuple to lambdify
    f = lambdify([], tup, 'sympy')
    # Capture the generated code
    captured = capsys.readouterr()
    # Generated code returns a tuple with commas between elements
    assert "return (1, 2, 3)" in captured.out
    # Return value is a tuple
    assert isinstance(f(), tuple)
    # Tuple elements are comma-separated
    assert len(f()) == len(tup)

    # Test fails with a non-tuple input or an empty tuple
    # Passing a non-tuple input
    with pytest.raises(TypeError):
        lambdify([], 1, 'sympy')
    # Passing an empty tuple
    with pytest.raises(TypeError):
        lambdify([], (), 'sympy')

    # Edge cases
    # Passing a tuple with a single element
    f_single = lambdify([], (1,), 'sympy')
    assert isinstance(f_single(), tuple)
    assert len(f_single()) == 1
