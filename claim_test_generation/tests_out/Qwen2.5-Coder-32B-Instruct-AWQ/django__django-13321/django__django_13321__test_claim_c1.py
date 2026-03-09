# Checklist TODO: Test passes with invalid session data.
# Checklist TODO: Decode method returns an empty dictionary.
# Checklist TODO: No exceptions are raised during execution.
import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c1():
    # Given: Invalid session data is provided to the decode method.
    invalid_session_data = [
        '',  # Test with an empty string as session data.
        'bad:encoded:value',  # Test with a string that is not base64 encoded.
        'Rmxhc2tkamM6YWxrZGpm',  # Test with a string that is base64 encoded but not a valid session dictionary.
    ]

    # Create a SessionBase instance
    session = SessionBase()

    for data in invalid_session_data:
        with pytest.subTest(data=data):
            # When: decode(session_data)
            result = session.decode(data)

            # Then: The method should return an empty dictionary.
            assert result == {}

            # No exceptions are raised during execution.
            # This is implicitly checked by the absence of an exception in the subTest.
