# Checklist TODO: Simulated socket error triggers ConnectionError.
# Checklist TODO: iter_content handles error gracefully across chunk sizes.
# Checklist TODO: decode_unicode parameter does not affect error handling.
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1(monkeypatch):
    # Given: A socket error occurs during a request
    r = Response()

    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    r.raw = RawMock()

    # When: iter_content is called on a Response object
    # Then: A requests.exceptions.ConnectionError is raised
    with pytest.raises(ConnectionError):
        list(r.iter_content())

    # Edge case: Test with different chunk sizes to ensure error handling is consistent
    for chunk_size in [1, 1024, 4096]:
        with pytest.raises(ConnectionError):
            list(r.iter_content(chunk_size=chunk_size))

    # Edge case: Test with decode_unicode set to True and False
    for decode_unicode in [True, False]:
        with pytest.raises(ConnectionError):
            list(r.iter_content(decode_unicode=decode_unicode))
