# Checklist TODO: Test must create a multi-line exception message.
# Checklist TODO: Test must capture the exception using pytest.raises.
# Checklist TODO: Test must assert that str(exc_info) equals the multi-line message.
import pytest

def test_claim_c1():
    # GIVEN: An exception with a multi-line message is raised and caught by pytest.raises
    multi_line_message = "A\nB\nC"

    # WHEN: Calling str() on the pytest.raises context manager's exception object (e)
    with pytest.raises(LookupError) as exc_info:
        raise LookupError(multi_line_message)

    # THEN: The returned string contains the full exception message (e.value) instead of the location and exception type
    assert str(exc_info.value) == multi_line_message  # Check that the message is correct
    assert str(exc_info) == f"<ExceptionInfo LookupError tblen=1>"  # Check that the str representation is as expected

    # Edge cases
    # Empty string as exception message
    with pytest.raises(LookupError) as exc_info_empty:
        raise LookupError("")
    assert str(exc_info_empty.value) == ""  # Check that the message is an empty string
    assert str(exc_info_empty) == f"<ExceptionInfo LookupError tblen=1>"  # Check that the str representation is as expected

    # Single line exception message
    single_line_message = "A"
    with pytest.raises(LookupError) as exc_info_single:
        raise LookupError(single_line_message)
    assert str(exc_info_single.value) == single_line_message  # Check that the message is correct
    assert str(exc_info_single) == f"<ExceptionInfo LookupError tblen=1>"  # Check that the str representation is as expected

    # Exception with no message
    with pytest.raises(LookupError) as exc_info_no_message:
        raise LookupError()
    assert str(exc_info_no_message.value) == ""  # Check that the message is an empty string
    assert str(exc_info_no_message) == f"<ExceptionInfo LookupError tblen=1>"  # Check that the str representation is as expected
