# Checklist TODO: Test shows correct message extraction pattern
# Checklist TODO: Exception type verification is implemented
# Checklist TODO: String representation includes full context
import pytest

def test_claim_c1():
    # Given: Raise LookupError with multi-line message
    with pytest.raises(LookupError) as e:
        # When: Raise the exception
        raise LookupError("A\nB\nC")
    
    # Then: Check the exception type and message
    assert e.type is LookupError  # Exception type verification is implemented
    assert "A\nB\nC" in str(e.value)  # str(e.value) contains 'A\nB\nC' substring
    assert str(e).startswith(f"<ExceptionInfo {e.type.__name__} tblen=")  # String representation includes full context
