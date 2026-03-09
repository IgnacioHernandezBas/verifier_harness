import pytest
from _pytest._io import saferepr

# Given: An object with a __repr__ method that raises an exception
class ExceptionRaisingObject:
    def __repr__(self):
        raise Exception("Test exception")

# When: SafeRepr.repr is called with the object
def test_claim_c1(monkeypatch):
    # Test raises the same exception as the object's __repr__ method
    with pytest.raises(Exception, match="Test exception"):
        saferepr.repr(ExceptionRaisingObject())

    # Test does not rely on internal implementation details
    # Test only verifies the behavioral property described in the claim
    # No additional assertions needed
