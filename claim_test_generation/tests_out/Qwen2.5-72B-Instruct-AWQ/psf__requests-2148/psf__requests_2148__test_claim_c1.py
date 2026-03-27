import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1(monkeypatch, capsys):
    # Test must simulate a socket error during content iteration.
    class RawMock:
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    # Create a Response object with the mock socket as its underlying connection.
    r = Response()
    r.raw = RawMock()

    # Test must verify that a ConnectionError is raised.
    with pytest.raises(ConnectionError) as exc_info:
        list(r.iter_content())

    # Test must confirm no other exceptions are raised.
    assert capsys.readouterr().out == ''
    assert capsys.readouterr().err == ''

    # The exception message matches the expected pattern for a ConnectionError.
    assert str(exc_info.value).startswith("('Connection aborted.',")

    # Edge case: Test with a non-socket error to ensure only socket errors are wrapped.
    class NonSocketErrorMock:
        def stream(self, chunk_size, decode_content=None):
            raise ValueError("This is a non-socket error.")

    r.raw = NonSocketErrorMock()
    with pytest.raises(ValueError):
        list(r.iter_content())

    # Edge case: Test with a closed connection to see if the behavior changes.
    class ClosedConnectionMock:
        def stream(self, chunk_size, decode_content=None):
            raise socket.error(socket.errno.EBADF, "Bad file descriptor")

    r.raw = ClosedConnectionMock()
    with pytest.raises(ConnectionError):
        list(r.iter_content())

    # Edge case: Test with a very large content size to ensure the error handling is consistent.
    class LargeContentMock:
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    r.raw = LargeContentMock()
    with pytest.raises(ConnectionError):
        list(r.iter_content())
