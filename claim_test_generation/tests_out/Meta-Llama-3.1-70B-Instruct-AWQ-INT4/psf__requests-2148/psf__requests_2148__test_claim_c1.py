import pytest
from requests import Response
import socket

# Checklist: Test raises requests.exceptions.ConnectionError
# Checklist: Test does not raise socket.error directly
# Checklist: Test handles non-streaming requests correctly

def test_claim_c1(capsys):
    # Given: A socket.error occurs during response content iteration (e.g., 'Connection reset by peer')
    # When: Response.iter_content() is called during a streaming request
    # Then: A requests.exceptions.ConnectionError is raised instead of the raw socket.error

    # Data setup: Create a mock response object
    r = Response()

    # Data setup: Configure the mock response to raise a socket.error during iteration
    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    r.raw = RawMock()

    # Data setup: Set up a streaming request
    r._content_consumed = False

    # Test raises requests.exceptions.ConnectionError
    with pytest.raises(ConnectionError):
        list(r.iter_content())

    # Test does not raise socket.error directly
    with pytest.raises(ConnectionError) as exc_info:
        list(r.iter_content())
    assert type(exc_info.value.__cause__) == socket.error

    # Test handles non-streaming requests correctly
    r._content_consumed = True
    try:
        list(r.iter_content())
    except ConnectionError:
        pytest.fail("ConnectionError raised for non-streaming request")
