import pytest

def test_claim_c1():
    # Raise LookupError with multi-line message
    with pytest.raises(LookupError) as exc_info:
        raise LookupError("A\nB\nC")
    # Convert pytest.raises context to string
    message = str(exc_info.value)
    # Verify all lines appear in output
    assert "A" in message
    assert "B" in message
    assert "C" in message
    assert message == "A\nB\nC"
