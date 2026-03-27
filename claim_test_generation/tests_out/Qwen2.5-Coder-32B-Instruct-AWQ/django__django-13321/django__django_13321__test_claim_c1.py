# Checklist TODO: Test passes without raising exceptions.
# Checklist TODO: Decoded result is an empty dictionary.
# Checklist TODO: Test works consistently across both buggy and fixed versions.
import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c1():
    # Given: An invalid session data string with incorrect base64 padding
    invalid_session_data = 'bad:encoded:value'
    
    # When: SessionStore.decode is called with the invalid data
    session_store = SessionBase()
    result = session_store.decode(invalid_session_data)
    
    # Then: No exception is raised and an empty dictionary is returned
    assert isinstance(result, dict)
    assert len(result) == 0
