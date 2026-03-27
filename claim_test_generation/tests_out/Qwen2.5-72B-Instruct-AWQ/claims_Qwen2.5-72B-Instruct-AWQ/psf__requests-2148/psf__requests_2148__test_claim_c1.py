# Checklist TODO: Simulate socket error during content iteration.
# Checklist TODO: Verify ConnectionError is raised.
# Checklist TODO: Ensure no other exceptions are unhandled.
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1(monkeypatch):
    # Given: A socket error occurs during a request
    # When: iter_content is called on a Response object
    # Then: A requests.exceptions.ConnectionError is raised

    # Data setup
    r = Response()
    r._content_consumed = False

    class RawMock:
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    r.raw = RawMock()

    # Edge cases
    def test_with_decode_unicode_true():
        with pytest.raises(ConnectionError):
            list(r.iter_content(decode_unicode=True))

    def test_with_small_chunk_size():
        with pytest.raises(ConnectionError):
            list(r.iter_content(chunk_size=1))

    def test_with_large_chunk_size():
        with pytest.raises(ConnectionError):
            list(r.iter_content(chunk_size=1024 * 1024))

    # Checklist
    # Simulate socket error during content iteration
    monkeypatch.setattr(r.raw, 'stream', RawMock().stream)

    # Verify ConnectionError is raised
    with pytest.raises(ConnectionError):
        list(r.iter_content())

    # Ensure no other exceptions are unhandled
    with pytest.raises(ConnectionError):
        list(r.iter_content(decode_unicode=True))
    with pytest.raises(ConnectionError):
        list(r.iter_content(chunk_size=1))
    with pytest.raises(ConnectionError):
        list(r.iter_content(chunk_size=1024 * 1024))
