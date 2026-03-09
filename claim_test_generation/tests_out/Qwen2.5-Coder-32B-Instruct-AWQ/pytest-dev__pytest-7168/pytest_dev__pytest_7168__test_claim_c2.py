import pytest
from pytest import fixture, mark
from src._pytest._io.saferepr import SafeRepr, _ellipsize

# Given: An object with a large string representation
# When: Calling SafeRepr.repr() on that object
# Then: SafeRepr.repr() should return a string that is no longer than maxsize

def test_claim_c2(tmpdir, monkeypatch, capsys):
    # Create an object with a string representation longer than maxsize
    large_string = "a" * 1000
    large_object = type('LargeObject', (object,), {'__repr__': lambda self: large_string})()

    # Define a maxsize parameter for SafeRepr initialization
    maxsize = 100

    # Initialize SafeRepr with maxsize
    safe_repr = SafeRepr(maxsize)

    # SafeRepr output length is within maxsize
    result = safe_repr.repr(large_object)
    assert len(result) <= maxsize

    # _ellipsize correctly truncates long strings
    truncated_string = _ellipsize(large_string, maxsize)
    assert len(truncated_string) <= maxsize
    assert truncated_string.endswith("...")

    # SafeRepr handles exceptions gracefully
    class ExceptionalObject:
        def __repr__(self):
            raise RuntimeError("Exception in repr")

    exceptional_object = ExceptionalObject()
    result_with_exception = safe_repr.repr(exceptional_object)
    assert "[RuntimeError() raised in repr()]" in result_with_exception

    # Test with maxsize set to 0
    safe_repr_zero = SafeRepr(0)
    result_zero = safe_repr_zero.repr(large_object)
    assert len(result_zero) <= 0

    # Test with maxsize set to a very large number
    safe_repr_large = SafeRepr(10000)
    result_large = safe_repr_large.repr(large_object)
    assert len(result_large) == len(large_string)
