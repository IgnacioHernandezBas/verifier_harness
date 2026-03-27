# Checklist TODO: Test must verify decode handles invalid data gracefully.
# Checklist TODO: Test must ensure _legacy_decode also handles invalid data without errors.
# Checklist TODO: Test must not rely on internal implementation details.
import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c1(monkeypatch):
    # GIVEN: An invalid session data string with incorrect base64 padding
    invalid_data = "invalid:base64:string"

    # Mock the necessary Django settings to avoid dependency issues
    monkeypatch.setattr("django.conf.settings.SESSION_SERIALIZER", "django.core.signing.JSONSerializer")

    # Create a session store instance
    session_store = SessionBase()

    # WHEN: SessionStore.decode is called with the invalid data
    # THEN: No exception is raised and an empty dictionary is returned
    result = session_store.decode(invalid_data)
    assert result == {}

    # WHEN: SessionStore._legacy_decode is called with the invalid data
    # THEN: No exception is raised and an empty dictionary is returned
    legacy_result = session_store._legacy_decode(invalid_data)
    assert legacy_result == {}

    # Edge cases
    # Test with an empty string as input
    empty_result = session_store.decode("")
    assert empty_result == {}

    # Test with a string containing only padding characters
    padding_result = session_store.decode("====")
    assert padding_result == {}

    # Test with a string that is a valid base64 but not a valid session data format
    valid_base64_result = session_store.decode(base64.b64encode(b'not:a:session:format').decode('ascii'))
    assert valid_base64_result == {}
