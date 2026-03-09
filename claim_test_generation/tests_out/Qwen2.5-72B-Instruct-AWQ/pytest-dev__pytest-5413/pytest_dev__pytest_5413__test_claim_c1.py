import pytest

def test_claim_c1():
    # Define a multi-line LookupError message 'A\nB\nC'.
    message = "A\nB\nC"
    
    # Use pytest.raises to capture the LookupError.
    with pytest.raises(LookupError) as e:
        raise LookupError(message)
    
    # Test raises LookupError with multi-line message.
    assert isinstance(e.value, LookupError)
    
    # Verify str(e) returns the full message.
    assert str(e.value) == message
    
    # Ensure no other exceptions are raised.
    with pytest.raises(LookupError):
        raise LookupError(message)
    
    # Test with a single-line message.
    single_line_message = "A"
    with pytest.raises(LookupError) as e_single:
        raise LookupError(single_line_message)
    assert str(e_single.value) == single_line_message
    
    # Test with an empty message.
    empty_message = ""
    with pytest.raises(LookupError) as e_empty:
        raise LookupError(empty_message)
    assert str(e_empty.value) == empty_message
    
    # Test with a non-LookupError exception.
    with pytest.raises(ValueError) as e_non_lookup:
        raise ValueError("Non-LookupError")
    assert str(e_non_lookup.value) == "Non-LookupError"
