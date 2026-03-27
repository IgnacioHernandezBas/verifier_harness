# Checklist TODO: Imports use 'from sympy import Symbol' not core.expr
# Checklist TODO: Comparison returns False when __repr__ matches symbol name
# Checklist TODO: No AttributeError raised during comparison
import pytest
from sympy import Symbol

def test_claim_c3():
    # Given: A sympy Symbol 'x' and an object C with __repr__ returning 'x'
    class C:
        def __repr__(self):
            return 'x'
    x = Symbol('x')
    c = C()

    # When: sympy.Symbol('x').__eq__(C()) is called
    result = x == c

    # Then: False is returned
    assert result is False
    assert isinstance(result, bool)
