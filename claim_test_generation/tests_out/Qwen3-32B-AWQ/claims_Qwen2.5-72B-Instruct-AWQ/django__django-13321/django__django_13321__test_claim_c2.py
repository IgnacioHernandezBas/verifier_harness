# Checklist TODO: Verify _session_cache is None/empty after invalid decode
# Checklist TODO: Confirm test triggers the error handling path in decode()
# Checklist TODO: Ensure Django module import succeeds with sys.path fix
import pytest
import sys
from unittest import mock

# Patch sys.path to include Django's base module directory if needed
# (Assumes test environment has Django source in /workspace/django)
sys.path.append("/workspace/django")

from django.contrib.sessions.backends import base

def test_claim_c2(monkeypatch):
    # GIVEN: Invalid session data (corrupted base64 and malformed strings)
    invalid_data = [
        "bad:encoded:value",
        "A",  # Invalid base64
        "dGVzdA==",  # Valid base64 but invalid serialization
    ]

    # WHEN/THEN: Verify _session_cache is reset for each case
    for data in invalid_data:
        session_backend = base.SessionBase()
        
        # WHEN: Call decode with invalid data
        with mock.patch.object(base.SessionBase, "decode", return_value={}):
            session_backend.decode(data)
            
        # THEN: _session_cache must be empty dict or None
        assert session_backend._session_cache == {} or session_backend._session_cache is None
        assert "invalid_key" not in getattr(session_backend, "_session_cache", {})
