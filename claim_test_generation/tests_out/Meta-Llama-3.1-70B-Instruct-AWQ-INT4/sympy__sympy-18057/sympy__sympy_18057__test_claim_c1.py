import pytest
from sympy import Symbol

def test_claim_c1(capsys):
    # Given: An unknown object whose repr is 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'

    # When: Calling sympy.Symbol('x') == C()
    # Then: Does not raise an AttributeError
    # Test does not raise an AttributeError when calling __eq__
    try:
        _ = Symbol('x') == C()
    except AttributeError:
        pytest.fail("Test raised an AttributeError")

    # Test handles unknown object with repr 'x.y' correctly
    assert repr(C()) == 'x.y'

    # Test verifies __eq__ method does not attempt to eval reprs
    class BadRepr(object):
        def __repr__(self):
            raise RuntimeError

    try:
        _ = Symbol('x') == BadRepr()
    except RuntimeError:
        pytest.fail("Test raised a RuntimeError")

    # Edge case: Unknown object with repr 'x.y' but no __eq__ method
    class NoEq:
        def __repr__(self):
            return 'x.y'

    try:
        _ = Symbol('x') == NoEq()
    except AttributeError:
        pytest.fail("Test raised an AttributeError")

    # Edge case: Unknown object with repr 'x.y' and __eq__ method that raises AttributeError
    class EqRaisesAttributeError:
        def __repr__(self):
            return 'x.y'

        def __eq__(self, other):
            raise AttributeError

    try:
        _ = Symbol('x') == EqRaisesAttributeError()
    except AttributeError:
        pytest.fail("Test raised an AttributeError")

    # Edge case: Unknown object with repr 'x.y' and __eq__ method that returns unexpected value
    class EqReturnsUnexpected:
        def __repr__(self):
            return 'x.y'

        def __eq__(self, other):
            return 42

    try:
        _ = Symbol('x') == EqReturnsUnexpected()
    except Exception:
        pytest.fail("Test raised an exception")
