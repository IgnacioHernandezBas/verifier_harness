# Checklist TODO: Verify no exceptions during invalid data decoding
# Checklist TODO: Confirm empty dict returned for malformed inputs
# Checklist TODO: Test both decode and legacy decoding paths
import pytest
import base64
from django.contrib.sessions.backends.base import SessionStore

def test_claim_c1():
    # Given: invalid base64 string with incorrect padding
    invalid_data = 'dGVzdA=='[:-1]  # Truncated base64 string
    store = SessionStore()

    # When: decode is called with invalid data
    result = store.decode(invalid_data)
    # Then: No exception raised, returns empty dict
    assert result == {}

    # When: _legacy_decode is called with invalid data
    result = store._legacy_decode(invalid_data)
    # Then: No exception raised, returns empty dict
    assert result == {}
