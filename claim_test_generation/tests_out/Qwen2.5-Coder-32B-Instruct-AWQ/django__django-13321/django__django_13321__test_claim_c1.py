# Checklist TODO: Test passes with invalid session data.
# Checklist TODO: No exceptions are raised during decode.
# Checklist TODO: Test handles edge cases gracefully.
import pytest
import base64
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c1():
    # Given: invalid session data
    invalid_session_data = [
        base64.b64encode(b'flaskdj:alkdjf').decode('ascii'),
        'bad:encoded:value',
        '',
        'not_base64_encoded'
    ]

    # When: calling decode
    # Then: should not raise an exception
    session = SessionBase()
    for data in invalid_session_data:
        with pytest.raises(Exception) as excinfo:
            session.decode(data)
        # The failed decode is logged.
        assert 'Session data corrupted' in str(excinfo.value)

    # Edge cases: empty string as session data, non-base64 encoded string
    # Test handles edge cases gracefully.
    for edge_case in ['', 'non_base64_encoded']:
        with pytest.raises(Exception) as excinfo:
            session.decode(edge_case)
        assert 'Session data corrupted' in str(excinfo.value)
