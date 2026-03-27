# Checklist TODO: decode() returns empty dict for invalid data
# Checklist TODO: Test works in both buggy and fixed versions
# Checklist TODO: No implementation detail dependencies
import pytest
import base64

from django.contrib.sessions.backends.base import SessionBase

def test_claim_c2():
    # Given: invalid session data
    invalid_data = base64.b64encode(b'corrupted_json').decode('ascii')
    
    # When: calling decode
    session = SessionBase()
    result = session.decode(invalid_data)
    
    # Then: should return an empty dictionary
    assert result == {}
