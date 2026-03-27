# Checklist TODO: Test setup configures Django settings.
# Checklist TODO: Invalid base64 data results in an empty dictionary.
# Checklist TODO: No exceptions are raised when processing invalid data.
import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c2(monkeypatch):
    # Test setup configures Django settings
    monkeypatch.setattr("django.conf.settings.SESSION_SERIALIZER", "django.contrib.sessions.serializers.JSONSerializer")

    # Create a session base instance
    session = SessionBase()

    # Invalid base64 data
    invalid_data = "invalid_base64_data"

    # Calling _legacy_decode with invalid base64 data returns an empty dictionary
    result = session._legacy_decode(invalid_data)
    assert result == {}

    # No exceptions are raised when processing invalid data
    assert True  # No exception was raised

    # Edge cases
    # Pass an empty string to _legacy_decode
    result = session._legacy_decode("")
    assert result == {}

    # Pass a None value to _legacy_decode
    result = session._legacy_decode(None)
    assert result == {}

    # Pass a very long string that is not valid base64 to _legacy_decode
    long_invalid_data = "a" * 1000
    result = session._legacy_decode(long_invalid_data)
    assert result == {}
