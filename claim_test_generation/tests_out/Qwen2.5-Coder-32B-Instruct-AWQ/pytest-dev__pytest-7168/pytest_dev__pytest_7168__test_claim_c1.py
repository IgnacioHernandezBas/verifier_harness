# Checklist TODO: Test raises the same exception as the object's __repr__.
# Checklist TODO: Verify no other exceptions are raised.
# Checklist TODO: Ensure test passes in both buggy and fixed versions.
import pytest
from _pytest._io.saferepr import SafeRepr

def test_claim_c1():
    # Given: An object with a __repr__ method that raises an exception.
    class SomeClass:
        def __repr__(self):
            raise ValueError("Custom error message")

    obj = SomeClass()

    # When: SafeRepr.repr is called with the object.
    # Then: The same exception raised in the __repr__ method is raised.
    with pytest.raises(ValueError) as excinfo:
        SafeRepr().repr(obj)

    # Verify the raised exception is the same as the one in __repr__
    assert str(excinfo.value) == "Custom error message"
