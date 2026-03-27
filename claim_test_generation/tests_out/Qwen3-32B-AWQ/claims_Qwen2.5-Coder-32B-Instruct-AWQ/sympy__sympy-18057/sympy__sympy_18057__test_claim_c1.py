# Checklist TODO: Use 'from sympy import Symbol' instead of core.expr
# Checklist TODO: Verify comparison doesn't raise AttributeError
# Checklist TODO: Test invalid repr handling in Symbol equality check
import pytest

def test_claim_c1():
    # Given: A SymPy Symbol and an object with a repr that evaluates to an invalid expression
    from sympy import Symbol
    class InvalidReprObject:
        def __repr__(self):
            return "x.y"  # Invalid attribute access when evaluated
    x = Symbol('x')
    obj = InvalidReprObject()

    # When: Performing equality comparison
    result = x == obj

    # Then: No AttributeError is raised, and comparison returns False
    assert result is False
