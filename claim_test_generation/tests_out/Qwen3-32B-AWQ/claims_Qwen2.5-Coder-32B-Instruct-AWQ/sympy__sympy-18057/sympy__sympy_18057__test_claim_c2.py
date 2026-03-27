# Checklist TODO: Comparison returns False for invalid-repr object
# Checklist TODO: No AttributeError during comparison
# Checklist TODO: Test handles custom __repr__ safely
import pytest
from sympy import Symbol

def test_claim_c2():
    # Given: A SymPy Symbol and an object with a repr that evaluates to an invalid expression.
    x = Symbol('x')

    class C:
        def __repr__(self):
            return 'x.y'

    # When: Comparing the Symbol to the object
    result = x == C()

    # Then: The comparison returns False
    assert result is False
