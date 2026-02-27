import pytest
from sympy import Symbol

def test_claim_c2():
    # Create a class C with __repr__ returning 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'

    # Instantiate sympy.Symbol('x')
    x = Symbol('x')

    # Test fails when comparing symbol with object repr 'x.y'
    assert (x == C()) is False

    # Symbol comparison with non-symbol returns False
    assert (x == 'x') is False
    assert (x == 1) is False
    assert (x == [1, 2, 3]) is False

    # Symbol comparison with different repr returns False
    class D:
        def __repr__(self):
            return 'x'

    assert (x == D()) is False
