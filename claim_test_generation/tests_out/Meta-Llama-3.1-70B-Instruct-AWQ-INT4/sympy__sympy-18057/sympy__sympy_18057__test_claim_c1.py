import pytest
from sympy import Symbol

def test_claim_c1(capsys):
    # Given: A sympy Symbol 'x' and an object C with __repr__ returning 'x.y'
    x = Symbol('x')
    class C:
        def __repr__(self):
            return 'x.y'

    # When: sympy.Symbol('x').__eq__(C()) is called
    # Then: No AttributeError is raised
    # Test passes without raising an AttributeError
    assert x.__eq__(C()) is False  # No AttributeError is raised

    # Test correctly handles the case where the object's __repr__ returns a string that sympy attempts to eval
    # Test correctly handles the case where the object's __repr__ returns a string that does not contain the Symbol's name
    class D:
        def __repr__(self):
            return 'y'
    assert x.__eq__(D()) is False  # No AttributeError is raised

    # Edge case: Comparing a sympy Symbol with an object whose __repr__ returns a string that sympy cannot eval
    class E:
        def __repr__(self):
            return 'invalid_expression'
    assert x.__eq__(E()) is False  # No AttributeError is raised
