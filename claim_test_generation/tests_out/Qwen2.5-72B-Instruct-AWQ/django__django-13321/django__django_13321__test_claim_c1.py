# Checklist TODO: Test must configure Django settings.
# Checklist TODO: Test must provide invalid session data to decode.
# Checklist TODO: Test must verify an empty dictionary is returned.
import pytest
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c1(monkeypatch):
    # GIVEN: Invalid session data is provided to the decode method.
    invalid_session_data = "invalid:session:data"
    empty_string_data = ""
    non_string_data = 12345
    non_base64_data = "not_base64_encoded"

    # Configure Django settings to avoid ImproperlyConfigured exceptions.
    settings.configure(SESSION_SERIALIZER='django.contrib.sessions.serializers.JSONSerializer')

    # Create a session base object to test the decode method.
    session = SessionBase()

    # WHEN: decode(session_data)
    # THEN: The method should return an empty dictionary.
    result = session.decode(invalid_session_data)
    assert result == {}

    # Test with an empty string as session data.
    result = session.decode(empty_string_data)
    assert result == {}

    # Test with a non-string type as session data.
    result = session.decode(non_string_data)
    assert result == {}

    # Test with a string that is not base64 encoded.
    result = session.decode(non_base64_data)
    assert result == {}

    # Test _legacy_decode method with invalid session data.
    result = session._legacy_decode(invalid_session_data)
    assert result == {}
