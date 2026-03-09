# Checklist TODO: Import sympy and define class C with __repr__ method.
# Checklist TODO: Create sympy Symbol 'x' and an instance of C.
# Checklist TODO: Assert that sympy.Symbol('x') == C() is True.
import pytest
from sympy import Symbol

# Import sympy and define class C with __repr__ method.
class C:
    def __repr__(self):
        return 'x'

# Create sympy Symbol 'x' and an instance of C.
def test_claim_c3():
    # Given: A SymPy Symbol and an object with a repr that evaluates to the same symbol.
    x = Symbol('x')
    c = C()

    # When: sympy.Symbol('x') == C()
    # Then: The comparison returns True.
    assert (x == c) is True

    # Edge cases
    # Test with a different string in the __repr__ method that does not match 'x'
    class D:
        def __repr__(self):
            return 'y'
    d = D()
    assert (x == d) is False

    # Test with a non-string object in the __repr__ method
    class E:
        def __repr__(self):
            return str(123)
    e = E()
    assert (x == e) is False

    # Test with a sympy Symbol that has a different name
    y = Symbol('y')
    assert (y == c) is False
