import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1(monkeypatch):
    # Simulate socket error during streaming.
    # Verify ConnectionError is raised.
    # Test with various parameters.

    # Given: A Response object with a mock raw stream that raises a socket error.
    r = Response()

    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    r.raw = RawMock()

    # When: iter_content is called with different parameters.
    # Then: A requests.exceptions.ConnectionError is raised.

    # Test with default parameters
    with pytest.raises(ConnectionError):
        list(r.iter_content())

    # Test with different chunk sizes
    for chunk_size in [1, 1024, 4096]:
        with pytest.raises(ConnectionError):
            list(r.iter_content(chunk_size=chunk_size))

    # Test with decode_content set to False
    with pytest.raises(ConnectionError):
        list(r.iter_content(decode_unicode=False))

    # Test with a non-existent URL to ensure the error is correctly raised
    # Note: This part is not directly related to the claim but ensures robustness
    # Since we cannot simulate a non-existent URL directly, we rely on the mock
    with pytest.raises(ConnectionError):
        list(r.iter_content())
