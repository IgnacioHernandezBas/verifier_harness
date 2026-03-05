# Checklist TODO: Test passes with correct LookupError message
# Checklist TODO: str(e) output matches expected format
# Checklist TODO: Test fails with incorrect LookupError message
import pytest

def test_claim_c1():
    # Given: A LookupError is raised within a pytest.raises context
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    
    # When: str(e) is called on the pytest.raises context variable e
    # Then: returns 'A\nB\nC'
    assert str(e.value) == "A\nB\nC"

    # Edge case: Empty error message
    with pytest.raises(LookupError) as e:
        raise LookupError("")
    assert str(e.value) == ""

    # Edge case: Multiline error message with different content
    with pytest.raises(LookupError) as e:
        raise LookupError("X\nY\nZ")
    assert str(e.value) == "X\nY\nZ"

    # Edge case: Error message with special characters
    with pytest.raises(LookupError) as e:
        raise LookupError("!@#\n$%^&*()")
    assert str(e.value) == "!@#\n$%^&*()"
