# Checklist TODO: Test uses pytest.raises context manager
# Checklist TODO: Verifies formatted string contains full multi-line message
# Checklist TODO: Differentiates between exception info and raw exception
import pytest

def test_claim_c1():
    # Given: Raise LookupError with multi-line message 'A\nB\nC'
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    
    # When: str(e) is called on the pytest.raises context variable e
    # Then: Verify exception info object construction
    assert e.type is LookupError  # e.type is LookupError
    
    # Verifies formatted string contains full multi-line message
    assert "A\nB\nC" in str(e.value)
    
    # Differentiates between exception info and raw exception
    assert str(e) != str(e.value)
