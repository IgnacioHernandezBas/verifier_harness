import pytest

def test_claim_c2():
    # Test passes with multi-line error message.
    # Given: A LookupError is raised with a multi-line error message 'A\nB\nC'.
    # When: calling str() on the pytest.raises context variable
    # Then: returns a string containing all lines of the error message.
    with pytest.raises(LookupError) as excinfo:
        raise LookupError("A\nB\nC")
    assert str(excinfo.value) == "A\nB\nC"

    # Test fails with single-line error message.
    # Given: A LookupError is raised with a single-line error message 'A'.
    # When: calling str() on the pytest.raises context variable
    # Then: returns a string containing only the first line of the error message.
    with pytest.raises(LookupError) as excinfo:
        raise LookupError("A")
    assert str(excinfo.value) == "A"

    # Test handles empty error message gracefully.
    # Given: A LookupError is raised with an empty error message.
    # When: calling str() on the pytest.raises context variable
    # Then: returns an empty string.
    with pytest.raises(LookupError) as excinfo:
        raise LookupError("")
    assert str(excinfo.value) == ""
