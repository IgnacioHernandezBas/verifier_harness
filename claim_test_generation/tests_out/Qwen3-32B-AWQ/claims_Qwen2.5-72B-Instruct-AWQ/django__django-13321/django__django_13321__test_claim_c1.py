# Checklist TODO: Test verifies BadSignature is raised for invalid data
# Checklist TODO: Test avoids Django settings dependencies beyond SECRET_KEY
# Checklist TODO: Test works in both buggy and fixed versions
import pytest
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.exceptions import BadSignature

def test_claim_c1(monkeypatch):
    # GIVEN: Set up minimal Django settings with a valid SECRET_KEY
    monkeypatch.setattr(settings, "SECRET_KEY", "testsecretkey", raising=False)
    
    # WHEN: Create a session instance and generate invalid session data
    session = SessionBase()
    valid_data = session.encode({"test": "data"})
    invalid_data = valid_data[:-1] + b"x"  # Corrupt the data
    
    # THEN: decode raises BadSignature for invalid data
    with pytest.raises(BadSignature):
        session.decode(invalid_data)
