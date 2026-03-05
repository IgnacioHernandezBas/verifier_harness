import pytest
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase

@pytest.mark.parametrize("invalid_data", [
    base64.b64encode(b'flaskdj:alkdjf').decode('ascii'),
    'bad:encoded:value',
    '',
    12345,
    b'not_base64'
])
def test_claim_c2(monkeypatch, invalid_data):
    # Configure Django settings in the test.
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', 'tests.settings')
    settings.configure()

    # Create a session object
    session = SessionBase()

    # Pass invalid session data to decode.
    result = session.decode(invalid_data)

    # Verify the return value is an empty dictionary.
    assert result == {}
