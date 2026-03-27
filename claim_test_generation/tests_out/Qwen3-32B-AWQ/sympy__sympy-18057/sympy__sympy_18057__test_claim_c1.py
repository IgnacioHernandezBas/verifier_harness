# Checklist TODO: Test confirms __eq__ handles custom repr objects safely
# Checklist TODO: No AttributeError occurs during cross-type comparison
# Checklist TODO: Verification aligns with issue reproduction scenario
import pytest
import sympy

def test_claim_c1():
    # Given: An unknown object whose repr is 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'
    # When: Calling sympy.Symbol('x') == C()
    x = sympy.Symbol('x')
    # Then: Does not raise an AttributeError
    assert (x == C()) is False
