# Checklist TODO: Verify decode() doesn't raise exceptions on invalid data
# Checklist TODO: Ensure settings mocking is isolated to test scope
# Checklist TODO: Confirm test passes in both buggy and fixed versions
import pytest
from django.conf import settings

def test_claim_c1(monkeypatch):
    # Setup: Mock minimal Django settings to avoid ImproperlyConfigured
    monkeypatch.setattr(settings, "SESSION_SERIALIZER", "django.contrib.sessions.serializers.JSONSerializer")
    
    # Given: Invalid session data inputs
    invalid_inputs = [
        "bad:encoded:value",  # Malformed string
        "non-base64-string",  # Not base64 encoded
        "123",  # Invalid base64
        "",  # Empty string
    ]
    
    # When/Then: decode() should not raise exceptions and return empty dict
    from django.contrib.sessions.backends.base import SessionBase
    session = SessionBase("dummy_key")
    
    for data in invalid_inputs:
        result = session.decode(data)
        assert result == {}, f"decode() returned non-empty dict for input: {data}"
