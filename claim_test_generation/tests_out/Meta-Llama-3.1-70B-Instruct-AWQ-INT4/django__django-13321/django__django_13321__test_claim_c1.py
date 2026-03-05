import pytest
from django.contrib.sessions.backends.base import SessionBase
from django.core.signing import BadSignature

# Checklist
# Test raises a BadSignature exception with invalid session data.
# Test does not crash the application with invalid session data.
# Test uses public APIs only and does not mock internal methods.

def test_claim_c1(capsys):
    # Given: An invalid session data is provided
    # When: decode is called with the invalid session data
    # Then: decode should raise a BadSignature exception

    # Data setup
    # Create a SessionBase object
    session = SessionBase()

    # Create invalid session data
    invalid_session_data = "invalid_session_data"

    # Test decode raises a BadSignature exception with invalid session data
    with pytest.raises(BadSignature):
        session.decode(invalid_session_data)

    # Test does not crash the application with invalid session data
    # The test will fail if the application crashes

    # Test uses public APIs only and does not mock internal methods
    # This test only uses public APIs and does not mock any internal methods
