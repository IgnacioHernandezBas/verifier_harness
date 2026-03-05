# Checklist TODO: Test decode with invalid data does not crash.
# Checklist TODO: Capture and verify log output for invalid data.
# Checklist TODO: Ensure no exceptions are raised during the test.
import pytest
from django.contrib.sessions.backends.base import SessionBase

@pytest.mark.parametrize("invalid_data", [
    base64.b64encode(b'flaskdj:alkdjf').decode('ascii'),
    'bad:encoded:value',
    '',
    None,
    'A' * 1000000  # Very large string
])
def test_claim_c1(monkeypatch, capsys, invalid_data):
    # GIVEN: invalid session data
    # WHEN: calling decode
    # THEN: should not raise an exception

    # Create a session backend instance
    session = SessionBase()

    # Monkeypatch logging to capture log messages
    with monkeypatch.context() as m:
        m.setattr('django.security.SuspiciousSession', lambda *args, **kwargs: None)
        with capsys.disabled():
            with pytest.raises(Exception) as exc_info:
                result = session.decode(invalid_data)
                assert result == {}, "decode should return an empty dictionary for invalid data"
            assert exc_info is None, "decode should not raise an exception with invalid data"

    # Capture and verify log output for invalid data
    captured = capsys.readouterr()
    assert 'Session data corrupted' in captured.out or 'Session data corrupted' in captured.err, "decode should log a warning for invalid data"

    # Ensure no exceptions are raised during the test
    assert not exc_info, "decode should not raise an exception with invalid data"
