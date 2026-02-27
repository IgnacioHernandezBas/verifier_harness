import pytest
from src._pytest._io.saferepr import SafeRepr

def test_claim_c2(tmpdir, monkeypatch, capsys):
    # Given: An object with a large string representation
    large_string = "a" * 1000
    class LargeStringObject:
        def __repr__(self):
            return large_string

    obj = LargeStringObject()
    maxsize = 100

    # When: Calling SafeRepr.repr() on that object
    safe_repr = SafeRepr(maxsize=maxsize)
    result = safe_repr.repr(obj)

    # Then: SafeRepr.repr() should return a string that is no longer than maxsize
    assert len(result) <= maxsize

    # Edge case: Object with string representation exactly equal to maxsize
    exact_string = "a" * maxsize
    class ExactStringObject:
        def __repr__(self):
            return exact_string

    obj_exact = ExactStringObject()
    result_exact = safe_repr.repr(obj_exact)
    assert len(result_exact) <= maxsize

    # Edge case: Object with string representation much larger than maxsize
    large_string_much_larger = "a" * 10000
    class LargeStringObjectMuchLarger:
        def __repr__(self):
            return large_string_much_larger

    obj_much_larger = LargeStringObjectMuchLarger()
    result_much_larger = safe_repr.repr(obj_much_larger)
    assert len(result_much_larger) <= maxsize

    # Edge case: Object with string representation smaller than maxsize
    small_string = "a" * 10
    class SmallStringObject:
        def __repr__(self):
            return small_string

    obj_small = SmallStringObject()
    result_small = safe_repr.repr(obj_small)
    assert len(result_small) <= maxsize

    # Check: SafeRepr.repr() returns a string within maxsize
    assert len(result) <= maxsize
    assert len(result_exact) <= maxsize
    assert len(result_much_larger) <= maxsize
    assert len(result_small) <= maxsize

    # Check: String is correctly ellipsized when exceeding maxsize
    assert result_much_larger.endswith("...")

    # Check: No errors occur with various string sizes
    assert not capsys.readouterr().err
