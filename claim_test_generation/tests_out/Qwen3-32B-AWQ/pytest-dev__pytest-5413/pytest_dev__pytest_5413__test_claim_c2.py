# Checklist TODO: Test confirms str() returns full error message
# Checklist TODO: Verifies multi-line content preservation
# Checklist TODO: Differentiates from partial/first-line-only output
import pytest

def test_claim_c2():
    # Given: A function that raises LookupError with multi-line message
    def raiser():
        raise LookupError("A\nB\nC")
    # When: Capturing the exception with pytest.raises
    with pytest.raises(LookupError) as exc_info:
        raiser()
    # Then: str(exc_info) contains all lines of the error message
    exc_str = str(exc_info)
    assert "A" in exc_str
    assert "B" in exc_str
    assert "C" in exc_str
    assert exc_str != "A"
