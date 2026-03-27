import pytest
import socket
from requests import Response
from requests.exceptions import ConnectionError

@pytest.fixture
def mock_response(monkeypatch):
    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise socket.error("Connection reset by peer")

    r = Response()
    r.raw = RawMock()
    return r

def test_claim_c1(mock_response):
    # Given: A socket.error occurs during response content iteration (e.g., 'Connection reset by peer')
    # When: Response.iter_content() is called during a streaming request
    # Then: A requests.exceptions.ConnectionError is raised instead of the raw socket.error

    # Mocked socket.error triggers ConnectionError
    with pytest.raises(ConnectionError) as excinfo:
        list(mock_response.iter_content())

    # ConnectionError wraps the original socket.error
    assert isinstance(excinfo.value.__cause__, socket.error)

    # No raw socket.error is exposed
    assert str(excinfo.value.__cause__) == "Connection reset by peer"
