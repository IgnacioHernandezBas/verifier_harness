# Checklist TODO: Test passes with invalid session data.
# Checklist TODO: Decode returns an empty dictionary.
# Checklist TODO: Handles various edge cases gracefully.
import pytest
import base64
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c2():
    # Given: invalid session data
    invalid_data = [
        '',  # empty string as session data
        'non-base64-encoded-string',  # non-base64 encoded string
        base64.b64encode(b'flaskdj:alkdjf').decode('ascii'),  # base64 encoded but corrupted string
    ]

    # When: calling decode
    session = SessionBase()
    for data in invalid_data:
        with pytest.subTest(data=data):
            with pytest.raises(Exception) as excinfo:
                result = session.decode(data)
            # Then: should return an empty dictionary
            assert result == {}

    # Additional check for logging
    for data in invalid_data:
        with pytest.subTest(data=data):
            with pytest.raises(Exception) as excinfo:
                with pytest.warns(UserWarning, match='Session data corrupted'):
                    session.decode(data)
