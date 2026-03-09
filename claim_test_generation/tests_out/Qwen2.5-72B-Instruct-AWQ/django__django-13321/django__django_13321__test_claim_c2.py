# Checklist TODO: Test must configure settings to avoid configuration errors.
# Checklist TODO: Test must call decode with invalid session data.
# Checklist TODO: Test must assert that the result is an empty dictionary.
import pytest
from django.contrib.sessions.backends.base import SessionBase
from django.conf import settings

def test_claim_c2(monkeypatch):
    # GIVEN: invalid session data
    invalid_data = [
        base64.b64encode(b'flaskdj:alkdjf').decode('ascii'),
        'bad:encoded:value',
        ''
    ]
    
    # Monkeypatch settings to avoid configuration issues
    monkeypatch.setattr(settings, 'SESSION_SERIALIZER', 'django.contrib.sessions.serializers.JSONSerializer')

    # WHEN: calling decode with invalid session data
    for data in invalid_data:
        with monkeypatch.context() as m:
            m.setattr(settings, 'SESSION_SERIALIZER', 'django.contrib.sessions.serializers.JSONSerializer')
            session = SessionBase()
            result = session.decode(data)
        
        # THEN: should return an empty dictionary
        assert result == {}
