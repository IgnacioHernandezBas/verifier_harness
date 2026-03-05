# Checklist TODO: Test captures LookupError with pytest.raises.
# Checklist TODO: String representation includes all lines of the error.
# Checklist TODO: No external fixtures or modules are required.
import pytest

def test_claim_c2():
    # Given: A LookupError is raised with a multi-line error message
    # Define a multi-line LookupError message
    error_message = "A\nB\nC"

    # When: calling str() on the pytest.raises context variable
    # Use pytest.raises to capture the exception context
    with pytest.raises(LookupError) as e:
        raise LookupError(error_message)

    # Then: returns a string containing all lines of the error message, not just 'A'
    # Test captures LookupError with pytest.raises
    assert isinstance(e, pytest.ExceptionInfo)
    # String representation includes all lines of the error
    assert 'A' in str(e.value)
    assert 'B' in str(e.value)
    assert 'C' in str(e.value)
    # No external fixtures or modules are required
