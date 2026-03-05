import pytest
from src._pytest._io.saferepr import SafeRepr

def test_claim_c2():
    # Test must initialize SafeRepr with a valid maxsize.
    maxsize = 100
    saferepr = SafeRepr(maxsize)

    # Create a large string object
    large_string = "a" * 200

    # Test must pass a large string to SafeRepr.repr().
    result = saferepr.repr(large_string)

    # Test must verify the output string length is <= maxsize.
    assert len(result) <= maxsize, "SafeRepr.repr() should return a string no longer than maxsize"

    # Test with maxsize set to 0
    saferepr_zero = SafeRepr(0)
    result_zero = saferepr_zero.repr(large_string)
    assert len(result_zero) == 0, "SafeRepr.repr() should return an empty string when maxsize is 0"

    # Test with an object that has no string representation
    class NoRepr:
        def __repr__(self):
            raise Exception("No representation available")

    no_repr_obj = NoRepr()
    saferepr_no_repr = SafeRepr(maxsize)
    result_no_repr = saferepr_no_repr.repr(no_repr_obj)
    assert len(result_no_repr) <= maxsize, "SafeRepr.repr() should return a string no longer than maxsize for objects with no string representation"

    # Test with a very small maxsize (e.g., 1)
    saferepr_small = SafeRepr(1)
    result_small = saferepr_small.repr(large_string)
    assert len(result_small) == 1, "SafeRepr.repr() should return a string of length 1 when maxsize is 1"
