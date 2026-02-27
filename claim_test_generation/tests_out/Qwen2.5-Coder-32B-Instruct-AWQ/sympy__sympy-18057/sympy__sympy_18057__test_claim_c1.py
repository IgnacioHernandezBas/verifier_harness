import pytest
from sympy import Symbol

# Test passes without raising AttributeError
# Symbol comparison with non-sympy object behaves as expected
# Edge cases do not cause unexpected behavior

def test_claim_c1():
    # Create a class C with __repr__ returning 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'

    # Instantiate sympy.Symbol('x')
    x = Symbol('x')

    # Instantiate C()
    c = C()

    # Given: An unknown object whose repr is 'x.y'
    # When: Calling sympy.Symbol('x') == C()
    # Then: Does not raise an AttributeError
    assert (x == c) is False

    # Edge case: Test with a class that raises an exception in __repr__
    class BadRepr:
        def __repr__(self):
            raise RuntimeError

    bad_repr = BadRepr()
    assert (x == bad_repr) is False

    # Edge case: Test with a class that returns a non-string from __repr__
    class NonStringRepr:
        def __repr__(self):
            return 123

    non_string_repr = NonStringRepr()
    assert (x == non_string_repr) is False

    # Edge case: Test with a class that returns a string that looks like a sympy expression
    class StringLikeRepr:
        def __repr__(self):
            return 'x'

    string_like_repr = StringLikeRepr()
    assert (x == string_like_repr) is False
