import pytest
from sympy import lambdify

def test_claim_c1(capsys):
    # GIVEN: A tuple with one element is passed to lambdify
    # WHEN: Calling lambdify with a tuple of one element
    f1 = lambdify([], (1,))

    # THEN: The generated code should return a tuple with a comma after the element
    # Test passes with a tuple of one element
    assert isinstance(f1(), tuple)  # Check if return value is a tuple
    assert len(f1()) == 1  # Check if tuple has one element
    captured = capsys.readouterr()
    assert "(1,)" in captured.out  # Check if generated code returns a tuple with a comma after the element

    # Test fails with a tuple of zero elements
    with pytest.raises(TypeError):
        lambdify([], ())

    # Test fails with a non-tuple object
    with pytest.raises(TypeError):
        lambdify([], 1)

    # Edge case: Passing a tuple with multiple elements
    f2 = lambdify([], (1, 2))
    assert isinstance(f2(), tuple)  # Check if return value is a tuple
    assert len(f2()) == 2  # Check if tuple has two elements
    captured = capsys.readouterr()
    assert "(1, 2)" in captured.out  # Check if generated code returns a tuple with a comma after the element
