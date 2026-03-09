import pytest
from sympy import Symbol

# Given: A SymPy Symbol and an object with a repr that evaluates to the same symbol.
# When: sympy.Symbol('x') == C()
# Then: The comparison returns True.

class C:
    def __repr__(self):
        return 'x'

class D:
    def __repr__(self):
        return 'y'

class E:
    pass

def test_claim_c3():
    # Create a class C with a __repr__ method that returns 'x'.
    # Instantiate sympy.Symbol('x').
    # Instantiate an object of class C.
    symbol_x = Symbol('x')
    c_instance = C()
    d_instance = D()
    e_instance = E()

    # Test passes when comparing sympy.Symbol('x') with C() where C().__repr__() == 'x'.
    assert symbol_x == c_instance

    # Test fails when comparing sympy.Symbol('x') with C() where C().__repr__() != 'x'.
    assert symbol_x != d_instance

    # Test fails when comparing sympy.Symbol('x') with an object without a __repr__ method.
    assert symbol_x != e_instance
