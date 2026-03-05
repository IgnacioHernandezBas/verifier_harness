# Checklist TODO: Import sympy and define class C with __repr__ returning 'x'.
# Checklist TODO: Compare sympy.Symbol('x') to C() and assert True.
# Checklist TODO: Test edge cases with different __repr__ outputs.
import pytest
from sympy import Symbol

class C:
    def __repr__(self):
        return 'x'

def test_claim_c3(monkeypatch):
    # Define a class C with a __repr__ method that returns 'x'
    # Create an instance of C
    c = C()
    # Create a sympy Symbol 'x'
    x = Symbol('x')

    # Compare sympy.Symbol('x') to C() and assert True
    assert x == c

    # Test edge cases with different __repr__ outputs
    class D:
        def __repr__(self):
            return 'y'
    d = D()
    assert x != d

    class E:
        def __repr__(self):
            return 123
    e = E()
    assert x != e

    # Test with a Symbol that has a different name
    y = Symbol('y')
    assert y != c
