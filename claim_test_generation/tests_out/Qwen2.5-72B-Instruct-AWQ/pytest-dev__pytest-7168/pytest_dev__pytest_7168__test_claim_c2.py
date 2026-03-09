import pytest
from pytest import fixture, raises

# Test must use SafeRepr from public API
# Test must verify the length of the returned string
# Test must handle edge cases and exceptions

def test_claim_c2(monkeypatch, capsys):
    # Create a class with a large string representation
    class LargeStringClass:
        def __repr__(self):
            return 'a' * 10000

    # Instantiate the class with a string longer than maxsize
    large_string_obj = LargeStringClass()

    # Define maxsize for the test
    maxsize = 100

    # Test with an object that raises an exception in __repr__
    class ExceptionClass:
        def __repr__(self):
            raise RuntimeError("repr failed")

    # Test with an object that returns a non-string in __repr__
    class NonStringClass:
        def __repr__(self):
            return 12345

    # Test with an empty string
    empty_string_obj = ""

    # Exercise SafeRepr and _ellipsize with large string objects
    saferepr = pytest.safe_repr
    result = saferepr(large_string_obj, maxsize=maxsize)

    # SafeRepr.repr() returns a string no longer than maxsize
    assert len(result) <= maxsize

    # SafeRepr.repr() handles non-string repr results gracefully
    result_non_string = saferepr(NonStringClass(), maxsize=maxsize)
    assert "TypeError" in result_non_string

    # SafeRepr.repr() correctly applies ellipsis to long strings
    assert "..." in result

    # Test with an object that raises an exception in __repr__
    result_exception = saferepr(ExceptionClass(), maxsize=maxsize)
    assert "RuntimeError" in result_exception

    # Test with an empty string
    result_empty = saferepr(empty_string_obj, maxsize=maxsize)
    assert result_empty == '""'
