import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1():
    # Create Response object with forced socket error
    r = Response()

    class RawMock:
        def stream(self, *args, **kwargs):
            raise socket.error("Test socket error")

    r.raw = RawMock()

    # Call iter_content and capture ConnectionError
    with pytest.raises(ConnectionError):
        # Verify exception wrapping and error propagation
        list(r.iter_content())
