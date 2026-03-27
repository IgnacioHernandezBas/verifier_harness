# Checklist TODO: Test passes with multi-line exception message.
# Checklist TODO: Asserts correct string representation of exception.
# Checklist TODO: Handles edge cases gracefully.
import pytest

def test_claim_c1():
    # Given: An exception with a multi-line message is raised and caught by pytest.raises
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")

    # When: Calling str() on the pytest.raises context manager's exception object (e)
    exception_str = str(e)

    # Then: The returned string contains the full exception message (e.value) instead of the location and exception type
    assert exception_str == "A\nB\nC"

    # Edge case: Exception message with special characters
    with pytest.raises(LookupError) as e:
        raise LookupError("Special chars: !@#$%^&*()")

    exception_str = str(e)
    assert exception_str == "Special chars: !@#$%^&*()"

    # Edge case: Empty exception message
    with pytest.raises(LookupError) as e:
        raise LookupError("")

    exception_str = str(e)
    assert exception_str == ""

    # Edge case: Very long exception message
    long_message = "a" * 1000
    with pytest.raises(LookupError) as e:
        raise LookupError(long_message)

    exception_str = str(e)
    assert exception_str == long_message
