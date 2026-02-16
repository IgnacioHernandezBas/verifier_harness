# Checklist TODO: SafeRepr.repr raises the same exception as the object's __repr__ method.
# Checklist TODO: Test passes with various exception types.
# Checklist TODO: Test confirms maxsize does not affect exception handling.
import pytest
from src._pytest._io.saferepr import SafeRepr

def test_claim_c1():
    # Create an object with a __repr__ method that raises an exception.
    class ExceptionalObject:
        def __repr__(self):
            raise ValueError("Custom repr error")

    # Instantiate SafeRepr with a valid maxsize argument.
    safe_repr = SafeRepr(maxsize=10)

    # Given: An object with a __repr__ method that raises an exception.
    obj = ExceptionalObject()

    # When: SafeRepr.repr is called with the object.
    # Then: The same exception raised in the __repr__ method is raised.
    with pytest.raises(ValueError) as excinfo:
        safe_repr.repr(obj)
    assert str(excinfo.value) == "Custom repr error"

    # Test with different types of exceptions raised in __repr__.
    class AnotherExceptionalObject:
        def __repr__(self):
            raise TypeError("Custom type error")

    obj = AnotherExceptionalObject()
    with pytest.raises(TypeError) as excinfo:
        safe_repr.repr(obj)
    assert str(excinfo.value) == "Custom type error"

    # Test with maxsize set to a very small value to ensure it doesn't interfere with the exception handling.
    safe_repr_small_maxsize = SafeRepr(maxsize=1)
    obj = ExceptionalObject()
    with pytest.raises(ValueError) as excinfo:
        safe_repr_small_maxsize.repr(obj)
    assert str(excinfo.value) == "Custom repr error"
