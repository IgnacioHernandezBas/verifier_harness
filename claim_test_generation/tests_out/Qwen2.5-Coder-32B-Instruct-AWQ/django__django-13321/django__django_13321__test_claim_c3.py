# Checklist TODO: Test fails with binascii.Error for incorrect padding.
# Checklist TODO: No other exceptions are raised.
# Checklist TODO: Test passes with valid session data (control test).
import pytest
import base64
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c3():
    # Given: An invalid session data with incorrect padding is provided
    incorrect_format_session_data = base64.b64encode(b'flaskdj:alkdjf').decode('ascii')[:-1]  # Remove one character to create incorrect padding
    no_padding_session_data = base64.b64encode(b'flaskdj:alkdjf').decode('ascii').replace('=', '')
    extra_padding_session_data = base64.b64encode(b'flaskdj:alkdjf').decode('ascii') + '='

    # When: decode is called with the invalid session data
    # Then: decode should raise a binascii.Error exception
    session = SessionBase()

    with pytest.raises(binascii.Error):
        session.decode(incorrect_format_session_data)

    with pytest.raises(binascii.Error):
        session.decode(no_padding_session_data)

    with pytest.raises(binascii.Error):
        session.decode(extra_padding_session_data)

    # Control test: Test passes with valid session data
    valid_session_data = base64.b64encode(b'flaskdj:alkdjf').decode('ascii')
    assert session.decode(valid_session_data) == {}
