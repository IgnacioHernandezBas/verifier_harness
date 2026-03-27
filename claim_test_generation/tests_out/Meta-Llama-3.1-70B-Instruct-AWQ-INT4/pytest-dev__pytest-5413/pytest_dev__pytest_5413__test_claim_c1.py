import pytest
from pytest import capsys

def test_claim_c1():
    # Given: An exception with a multi-line message is raised and caught by pytest.raises
    # When: Calling str() on the pytest.raises context manager's exception object (e)
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")

    # Then: The returned string contains the full exception message (e.value) instead of the location and exception type
    assert "A\nB\nC" in str(e.value)

    # Checklist: Test passes with multi-line exception message
    assert "LookupError" not in str(e.value)

    # Checklist: Test fails with incorrect exception message
    with pytest.raises(AssertionError):
        assert "D\nE\nF" in str(e.value)

    # Checklist: Test handles edge cases correctly
    # Single-line exception message
    with pytest.raises(LookupError) as e:
        raise LookupError("Single line")
    assert "Single line" in str(e.value)

    # Empty exception message
    with pytest.raises(LookupError) as e:
        raise LookupError("")
    assert "" == str(e.value)

    # Exception message with non-string content
    with pytest.raises(LookupError) as e:
        raise LookupError([1, 2, 3])
    assert "[1, 2, 3]" in str(e.value)
