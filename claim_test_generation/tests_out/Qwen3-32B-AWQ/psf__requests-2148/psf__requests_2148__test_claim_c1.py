# Checklist TODO: Response object is properly initialized with error state
# Checklist TODO: ConnectionError is raised during iter_content()
# Checklist TODO: Socket error context is preserved in the exception
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1():
    # GIVEN: A socket error occurs during a request
    r = Response()
    class RawMock:
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()
    r.raw = RawMock()
    
    # WHEN: Calling Response.iter_content()
    # THEN: A requests.exceptions.ConnectionError is raised
    with pytest.raises(ConnectionError) as exc_info:
        list(r.iter_content())
    
    # Assertion: The raised exception is an instance of requests.exceptions.ConnectionError
    assert isinstance(exc_info.value, ConnectionError)
