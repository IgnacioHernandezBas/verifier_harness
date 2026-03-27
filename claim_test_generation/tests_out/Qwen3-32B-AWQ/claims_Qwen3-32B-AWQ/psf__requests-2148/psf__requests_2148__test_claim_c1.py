# Checklist TODO: Verify socket.error is wrapped in ConnectionError during iter_content()
# Checklist TODO: Use monkeypatch to simulate mid-iteration socket failure
# Checklist TODO: Confirm original exception type is preserved in the wrapped error
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1():
    # Given: A socket.error occurs during response content iteration
    r = Response()
    class RawMock:
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()
    r.raw = RawMock()
    # When: Response.iter_content() is called during a streaming request
    # Then: A requests.exceptions.ConnectionError is raised instead of the raw socket.error
    with pytest.raises(ConnectionError):
        list(r.iter_content())
