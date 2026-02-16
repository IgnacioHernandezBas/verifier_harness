import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c1():
    # GIVEN: Invalid session data string to simulate corrupted or malformed session data.
    invalid_session_data = "invalid_base64_string"
    empty_session_data = ""
    non_string_session_data = 12345
    incorrect_base64_session_data = "aGVsbG8gd29ybGQh"  # "hello world!" in base64, but not a valid session data

    # Create a SessionBase instance to access the decode and _legacy_decode methods
    session = SessionBase()

    # WHEN: decode(session_data) with invalid session data
    # THEN: The method should return an empty dictionary.
    assert session.decode(invalid_session_data) == {}
    assert session.decode(empty_session_data) == {}
    assert session.decode(non_string_session_data) == {}
    assert session.decode(incorrect_base64_session_data) == {}

    # WHEN: _legacy_decode(session_data) with invalid session data
    # THEN: The method should return an empty dictionary.
    assert session._legacy_decode(invalid_session_data) == {}
    assert session._legacy_decode(empty_session_data) == {}
    assert session._legacy_decode(non_string_session_data) == {}
    assert session._legacy_decode(incorrect_base64_session_data) == {}

    # Test passes with invalid session data input.
    # No exceptions are raised during execution.
    # Both decode and _legacy_decode methods return empty dictionaries.
