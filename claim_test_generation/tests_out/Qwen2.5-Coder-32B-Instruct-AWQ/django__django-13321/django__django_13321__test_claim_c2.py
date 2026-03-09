# Checklist TODO: Test passes with invalid session data.
# Checklist TODO: Function returns an empty dictionary.
# Checklist TODO: Test does not depend on internal implementation details.
import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c2():
    # Given: invalid session data
    invalid_session_data = base64.b64encode(b'flaskdj:alkdjf').decode('ascii')
    empty_string_data = ''
    non_base64_data = 'bad:encoded:value'

    # When: calling decode
    session = SessionBase()

    # Then: should return an empty dictionary
    assert session.decode(invalid_session_data) == {}
    assert session.decode(empty_string_data) == {}
    assert session.decode(non_base64_data) == {}
