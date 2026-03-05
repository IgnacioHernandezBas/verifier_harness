import pytest
from sympy.core.expr import Expr
from sympy import Symbol

def test_claim_c1():
    # GIVEN: An unknown object whose repr is 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'
    
    # WHEN: Calling sympy.Symbol('x') == C()
    x = Symbol('x')
    c = C()

    # THEN: Does not raise an AttributeError
    with pytest.raises(AssertionError):
        assert x == c

    # Test with a class C that has a __repr__ method returning a non-string
    class C2:
        def __repr__(self):
            return 123  # Non-string repr

    c2 = C2()
    with pytest.raises(AssertionError):
        assert x == c2

    # Test with a class C that has a __repr__ method raising an exception
    class C3:
        def __repr__(self):
            raise RuntimeError

    c3 = C3()
    with pytest.raises(AssertionError):
        assert x == c3

    # Test with a class C that has a __repr__ method returning a very long string
    class C4:
        def __repr__(self):
            return 'x' * 10000  # Very long string

    c4 = C4()
    with pytest.raises(AssertionError):
        assert x == c4

    # Test must verify no AttributeError is raised
    # Test must ensure __eq__ does not evaluate repr of C()
    # Test must pass with the expected behavior of __eq__
