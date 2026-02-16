# Checklist TODO: Test passes with the specified multi-line message.
# Checklist TODO: str(e) returns the exact error message without additional context.
# Checklist TODO: Test fails with incorrect or partial error messages.
import pytest

def test_claim_c1():
    # Given: A LookupError is raised with the message 'A\nB\nC' inside a pytest.raises context.
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    
    # When: str(e) is called on the pytest.raises context variable.
    error_message = str(e.value)
    
    # Then: The full error message 'A\nB\nC' is returned.
    assert error_message == "A\nB\nC"
