# Checklist TODO: Test verifies lambdify returns tuple when given tuple expr
# Checklist TODO: Output matches expected (1, 2) structure
# Checklist TODO: Confirms type and length of returned tuple
import pytest
from sympy.utilities.lambdify import lambdify

def test_claim_c2():
    # Given: empty args and tuple expr
    args = []
    expr = (1, 2)
    # When: create lambda function and call it
    func = lambdify(args, expr)
    lambda_result = func()
    # Then: check assertions
    assert lambda_result == (1, 2)
    assert isinstance(lambda_result, tuple)
    assert len(lambda_result) == 2
