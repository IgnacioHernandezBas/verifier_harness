# Checklist TODO: Test passes with invalid session data input.
# Checklist TODO: No exceptions are raised during execution.
# Checklist TODO: Both decode and _legacy_decode methods return empty dictionaries.
import pytest
from django.contrib.sessions.backends.base import SessionBase
from django.conf import settings

def test_claim_c1():
    # GIVEN: Invalid session data is provided to the decode method.
    invalid_session_data = [
        base64.b64encode(b'flaskdj:alkdjf').decode('ascii'),
        'bad:encoded:value',
        '',
        12345,
        None
    ]

    # Configure Django settings to avoid ImproperlyConfigured exception
    settings.configure(SESSION_SERIALIZER='django.contrib.sessions.serializers.JSONSerializer')

    # Create a SessionBase instance
    session = SessionBase()

    for data in invalid_session_data:
        with pytest.subTest(data=data):
            # WHEN: decode(session_data)
            result_decode = session.decode(data)
            # THEN: The method should return an empty dictionary.
            assert isinstance(result_decode, dict)
            assert len(result_decode) == 0

            # WHEN: _legacy_decode(session_data)
            result_legacy_decode = session._legacy_decode(data)
            # THEN: The method should return an empty dictionary.
            assert isinstance(result_legacy_decode, dict)
            assert len(result_legacy_decode) == 0
