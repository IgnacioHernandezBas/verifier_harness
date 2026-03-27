# Checklist TODO: Document chosen strategy in comments.
# Checklist TODO: Assert observable(s) quoted in plan.
# Checklist TODO: Explain fixtures or inputs used.
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError
import socket

def test_claim_c1():
    # GIVEN: A socket error occurs during a request
    r = Response()
    class RawMock:
        def stream(self, chunk_size, decode_content=None):
            # WHEN: iter_content is called on a Response object
            raise socket.error("Simulated socket error")

    r.raw = RawMock()
    # THEN: A requests.exceptions.ConnectionError is raised
    with pytest.raises(ConnectionError):
        list(r.iter_content())
