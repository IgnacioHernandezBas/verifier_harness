# Checklist TODO: Symbol and custom object are correctly instantiated
# Checklist TODO: Equality check returns False when __repr__ matches
# Checklist TODO: No false positives with different __repr__ values
import pytest
import sympy


def test_claim_c2():
    # Given: Custom class C with __repr__ returning 'x'
    class C:
        def __repr__(self):
            return 'x'

    x = sympy.Symbol('x')
    c_instance = C()

    # When: Calling __eq__ between sympy.Symbol('x') and C()
    result = x == c_instance

    # Then: Returns False
    assert result is False
    assert repr(c_instance) == 'x'
