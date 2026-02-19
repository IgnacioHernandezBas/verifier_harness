# Checklist TODO: Test fails with the current code, showing incorrect error message.
# Checklist TODO: Test passes with the fixed code, returning the full error message.
# Checklist TODO: Verify the assertion matches the actual return type and structure.
import pytest

def test_claim_c1():
    # Given: A LookupError is raised with a multi-line message inside a pytest.raises context.
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    
    # When: str(e) is called where e is the pytest.raises context variable.
    error_message = str(e)
    
    # Then: The full error message 'A\nB\nC' is returned.
    assert error_message == "A\nB\nC"
