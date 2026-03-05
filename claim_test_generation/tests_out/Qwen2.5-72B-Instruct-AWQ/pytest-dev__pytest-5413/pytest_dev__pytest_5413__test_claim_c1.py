# Checklist TODO: Test must raise a LookupError with a multi-line message.
# Checklist TODO: Test must capture the exception using pytest.raises.
# Checklist TODO: Test must verify str(e) returns the full error message.
import pytest

def test_claim_c1():
    # Given: A LookupError is raised with a multi-line error message
    error_message = "A\nB\nC"
    
    # When: calling str() on the pytest.raises context variable
    with pytest.raises(LookupError) as e:
        raise LookupError(error_message)
    
    # Then: str(e) returns the full multi-line error message
    assert str(e.value) == error_message, "str(e) should return the full multi-line error message"
    
    # Then: str(e) includes all lines of the error message
    assert all(line in str(e.value) for line in error_message.split("\n")), "str(e) should include all lines of the error message"
    
    # Then: str(e) matches the expected multi-line string
    assert str(e.value) == "A\nB\nC", "str(e) should match the expected multi-line string"
