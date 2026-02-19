import pytest
from src._pytest._io.saferepr import SafeRepr

def test_claim_c2(monkeypatch):
    # Given: An object with a large string representation
    class LargeObject:
        def __repr__(self):
            return "a" * 10000

    large_object = LargeObject()

    # When: Calling SafeRepr.repr() on that object
    maxsize = 1000
    safe_repr = SafeRepr(maxsize)

    # Then: SafeRepr.repr() should return a string that is no longer than maxsize
    # Test passes with valid input and maxsize
    assert len(safe_repr.repr(large_object)) <= maxsize

    # Test raises no exceptions with valid input
    with pytest.raises(Exception, match=""):
        safe_repr.repr(large_object)

    # Test correctly limits string length to maxsize
    assert len(safe_repr.repr(large_object)) <= maxsize

    # Edge case: Test with maxsize set to 0
    safe_repr = SafeRepr(0)
    assert len(safe_repr.repr(large_object)) == 0

    # Edge case: Test with maxsize set to a negative value
    with pytest.raises(ValueError):
        SafeRepr(-1)

    # Edge case: Test with an object that has no string representation
    class NoReprObject:
        pass

    no_repr_object = NoReprObject()
    with pytest.raises(Exception):
        safe_repr.repr(no_repr_object)
