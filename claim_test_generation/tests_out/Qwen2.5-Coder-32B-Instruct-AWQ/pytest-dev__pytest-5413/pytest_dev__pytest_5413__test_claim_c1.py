import pytest

def test_claim_c1():
    # Test verifies str() returns full multi-line error message
    # Given: A LookupError is raised with a multi-line error message
    multi_line_error_message = "A\nB\nC"
    with pytest.raises(LookupError) as excinfo:
        raise LookupError(multi_line_error_message)
    # When: calling str() on the pytest.raises context variable
    error_str = str(excinfo.value)
    # Then: returns the full error message, including all lines
    assert error_str == multi_line_error_message

    # Handles error messages without newline characters
    # Given: A LookupError is raised with a single-line error message
    single_line_error_message = "SingleLineError"
    with pytest.raises(LookupError) as excinfo:
        raise LookupError(single_line_error_message)
    # When: calling str() on the pytest.raises context variable
    error_str = str(excinfo.value)
    # Then: returns the full error message, including all lines
    assert error_str == single_line_error_message

    # Consistently includes all lines in the error message
    # Given: A LookupError is raised with a multi-line error message including leading and trailing newlines
    multi_line_error_message_with_newlines = "\nA\nB\nC\n"
    with pytest.raises(LookupError) as excinfo:
        raise LookupError(multi_line_error_message_with_newlines)
    # When: calling str() on the pytest.raises context variable
    error_str = str(excinfo.value)
    # Then: returns the full error message, including all lines
    assert error_str == multi_line_error_message_with_newlines
