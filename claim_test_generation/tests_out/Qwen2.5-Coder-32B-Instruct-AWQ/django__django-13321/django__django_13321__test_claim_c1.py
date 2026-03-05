# Checklist TODO: Test fails with NameError for undefined base64
# Checklist TODO: decode raises BadSignature with invalid session data
# Checklist TODO: Test passes with correct exception handling
import pytest
import base64
from django.contrib.sessions.backends.base import SessionBase
from django.core.signing import BadSignature

def test_claim_c1():
    # Given: An invalid session data is provided
    incorrect_format_session_data = base64.b64encode(b'flaskdj:alkdjf').decode('ascii')
    empty_session_data = ''
    incorrect_base64_session_data = 'bad:encoded:value'

    # When: decode is called with the invalid session data
    # Then: decode should raise a BadSignature exception
    session = SessionBase()

    with pytest.raises(BadSignature):
        session.decode(incorrect_format_session_data)

    with pytest.raises(BadSignature):
        session.decode(empty_session_data)

    with pytest.raises(BadSignature):
        session.decode(incorrect_base64_session_data)
