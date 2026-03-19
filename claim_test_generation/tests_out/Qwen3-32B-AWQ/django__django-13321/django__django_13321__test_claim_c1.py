# Checklist TODO: Dependencies installed for Django and ASGI
# Checklist TODO: Module import path correctly configured
# Checklist TODO: Exception handling verified with corrupted data
import pytest
import sys
import os
import base64

# Add repo path to sys.path for module visibility
sys.path.insert(0, "/fs/nexus-scratch/ihbas/repos_claim_cache/django__django/35b03788b0607c1f8d2b64e4fa9e1669b0907ea4")

# Import dependencies after path adjustment
from django.contrib.sessions.backends.base import BaseSession
from django.contrib.sessions.exceptions import BadSignature

def test_claim_c1():
    # Given: An invalid session data is provided
    invalid_data = base64.b64encode(b'corrupted:session:data').decode('ascii')
    
    # When/Then: decode should raise BadSignature exception
    session = BaseSession()
    with pytest.raises(BadSignature):
        session.decode(invalid_data)
