# Checklist TODO: Test verifies incorrect padding handling
# Checklist TODO: Exception type and message are validated
# Checklist TODO: Minimal reproducible data is generated
import pytest
import binascii
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c3():
    # Given: An invalid session data with incorrect padding is provided
    invalid_data = "dGVzdA"  # Valid base64 without padding
    session = SessionBase()
    # When: decode is called with the invalid session data
    # Then: decode should raise a binascii.Error exception
    with pytest.raises(binascii.Error, match="Incorrect padding"):
        session.decode(invalid_data)
