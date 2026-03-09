# Checklist TODO: Define a class with a __repr__ method that raises an exception.
# Checklist TODO: Instantiate the class and pass the instance to SafeRepr.repr.
# Checklist TODO: Assert that the same exception is raised by SafeRepr.repr.
import pytest
from pytest import raises

# Define a class with a __repr__ method that raises an exception.
class ExceptionRaiser:
    def __repr__(self):
        raise ValueError("This is a test exception")

# Instantiate the class and pass the instance to SafeRepr.repr.
def test_claim_c1(monkeypatch):
    # GIVEN: An object with a __repr__ method that raises an exception.
    obj = ExceptionRaiser()

    # WHEN: SafeRepr.repr is called with the object.
    # THEN: The same exception raised in the __repr__ method is raised.
    with raises(ValueError, match="This is a test exception"):
        saferepr = pytest.safe_repr(obj)
