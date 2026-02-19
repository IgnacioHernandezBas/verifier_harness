import pytest
from src._pytest._io.saferepr import SafeRepr

def test_claim_c1(monkeypatch):
    # Given: An object with a __repr__ method that raises an exception
    class ExceptionRaisingObject:
        def __repr__(self):
            raise RuntimeError("Test exception")

    # When: Calling SafeRepr.repr() on that object
    exception_raising_object = ExceptionRaisingObject()
    safe_repr = SafeRepr(maxsize=1000)
    result = safe_repr.repr(exception_raising_object)

    # Then: SafeRepr.repr() should return a string containing information about the exception
    assert "RuntimeError" in result
    assert "Test exception" in result

    # Test passes when __repr__ raises an exception
    assert "ExceptionRaisingObject" in result

    # Test fails when __repr__ does not raise an exception
    class NonExceptionRaisingObject:
        def __repr__(self):
            return "NonExceptionRaisingObject"
    non_exception_raising_object = NonExceptionRaisingObject()
    result = safe_repr.repr(non_exception_raising_object)
    assert "NonExceptionRaisingObject" in result

    # Test handles different types of exceptions raised by __repr__
    class DifferentExceptionRaisingObject:
        def __repr__(self):
            raise ValueError("Different test exception")
    different_exception_raising_object = DifferentExceptionRaisingObject()
    result = safe_repr.repr(different_exception_raising_object)
    assert "ValueError" in result
    assert "Different test exception" in result
