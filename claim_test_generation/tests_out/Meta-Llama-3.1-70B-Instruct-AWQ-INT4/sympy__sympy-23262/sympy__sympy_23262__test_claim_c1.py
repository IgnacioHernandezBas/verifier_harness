import pytest
from sympy import symbols, lambdify

def test_claim_c1(capsys):
    # GIVEN: A single-element tuple is provided as the argument to `lambdify`.
    # WHEN: The `lambdify` function is called with an empty list and a single-element tuple.
    # THEN: The generated lambda function returns a tuple with a single element, represented as `(1,)`.
    
    # Create a single-element tuple as input to lambdify
    single_element_tuple = (1,)
    
    # Create an empty list as the first argument to lambdify
    empty_list = []
    
    # Create a SymPy expression as the second argument to lambdify
    x = symbols('x')
    sympy_expression = x
    
    # Exercise lambdify with single-element tuple
    lambda_func = lambdify(empty_list, single_element_tuple)
    
    # Test passes when a single-element tuple is provided to lambdify
    assert isinstance(lambda_func(), tuple)
    
    # The generated lambda function returns a tuple with a single element
    assert len(lambda_func()) == 1
    
    # The test fails when a non-tuple input is passed to lambdify
    with pytest.raises(TypeError):
        lambdify(empty_list, 1)
    
    # Passing a tuple with multiple elements to lambdify
    multi_element_tuple = (1, 2)
    lambda_func_multi = lambdify(empty_list, multi_element_tuple)
    assert len(lambda_func_multi()) == 2
    
    # Passing a non-SymPy expression as the second argument to lambdify
    non_sympy_expression = 1
    with pytest.raises(TypeError):
        lambdify(empty_list, non_sympy_expression)
