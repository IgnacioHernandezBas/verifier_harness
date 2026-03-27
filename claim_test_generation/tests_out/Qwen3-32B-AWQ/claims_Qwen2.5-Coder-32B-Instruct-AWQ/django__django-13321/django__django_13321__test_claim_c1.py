# Checklist TODO: Decode invalid data returns empty dict
# Checklist TODO: No exceptions raised for bad input
# Checklist TODO: Handles multiple invalid formats consistently
import pytest
from django.contrib.sessions.backends.base import BaseSession

def test_claim_c1():
    # Given: Invalid session data
    session = BaseSession(session_key="dummy_key", session_data="dummy_data")
    invalid_inputs = ["invalid_data", "garbage_input", "A"]

    # When/Then: decode returns empty dict without exceptions
    for input_data in invalid_inputs:
        result = session.decode(input_data)
        assert result == {}, f"Failed for input: {input_data}"

    # Edge case: empty string input
    result = session.decode("")
    assert result == {}

    # Edge case: non-string input (test with bytes)
    result = session.decode(b"non_string_input")
    assert result == {}
