# Checklist TODO: Test fails if no exception is raised.
# Checklist TODO: Test passes if the correct exception is raised.
# Checklist TODO: Test fails if a different exception is raised.
import pytest
from pytest import raises

def test_claim_c1(monkeypatch):
    # Given: An object with a __repr__ method that raises an exception.
    class SomeClass:
        def __repr__(self):
            raise ValueError("Custom error message")

    # When: SafeRepr.repr is called with the object.
    # Then: The same exception raised in the __repr__ method is raised.
    with raises(ValueError) as excinfo:
        from _pytest._io.saferepr import SafeRepr
        safe_repr = SafeRepr()
        safe_repr.repr(SomeClass())

    # Assert the correct exception is raised.
    assert str(excinfo.value) == "Custom error message"
