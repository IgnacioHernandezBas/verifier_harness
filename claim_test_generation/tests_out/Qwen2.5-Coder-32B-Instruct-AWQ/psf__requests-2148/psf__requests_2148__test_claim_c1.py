# Checklist TODO: Simulate socket error and verify ConnectionError.
# Checklist TODO: Check behavior with various chunk sizes.
# Checklist TODO: Test with decode_content=True for coverage.
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1(monkeypatch):
    # Given: A socket error occurs during the read operation in the response content streaming.
    r = Response()

    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    r.raw = RawMock()

    # When: self.raw.stream(chunk_size, decode_content=True) is called in the iter_content method
    # Then: A requests.exceptions.ConnectionError is raised.
    with pytest.raises(ConnectionError):
        list(r.iter_content(chunk_size=1, decode_unicode=False))

    # Check behavior with various chunk sizes.
    for chunk_size in [1, 1024, 4096]:
        with pytest.raises(ConnectionError):
            list(r.iter_content(chunk_size=chunk_size, decode_unicode=False))

    # Test with decode_content=True for coverage.
    with pytest.raises(ConnectionError):
        list(r.iter_content(chunk_size=1, decode_unicode=True))
