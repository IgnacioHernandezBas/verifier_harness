# Checklist TODO: Test raises a test failure or error, not an INTERNALERROR.
# Checklist TODO: Exception in __repr__ is caught and handled.
# Checklist TODO: Test provides a meaningful error message.
import pytest
from pytest import raises

def test_claim_c1(monkeypatch):
    # GIVEN: An instance of SomeClass is created and an attribute is accessed, which raises an exception in __getattribute__ and __repr__.
    class SomeClass:
        def __getattribute__(self, attr):
            raise RuntimeError("Attribute access error")

        def __repr__(self):
            raise RuntimeError("Repr error")

    obj = SomeClass()

    # WHEN: pytest runs the test function `test`
    # THEN: pytest should raise a test failure or error, not an INTERNALERROR.
    with raises(RuntimeError) as excinfo:
        repr(obj)

    # The exception raised in __repr__ should be caught and handled by _format_repr_exception.
    # The test should not crash and should provide a meaningful error message.
    assert "Repr error" in str(excinfo.value)
