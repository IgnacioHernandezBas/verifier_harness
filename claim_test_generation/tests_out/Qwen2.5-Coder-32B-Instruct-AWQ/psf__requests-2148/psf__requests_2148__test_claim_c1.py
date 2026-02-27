# Checklist TODO: Test raises ConnectionError on socket error
# Checklist TODO: Verify normal behavior without errors
# Checklist TODO: Check for other error types
import pytest
import requests
from requests.exceptions import ConnectionError
from requests.models import Response

@pytest.fixture
def mock_response(monkeypatch):
    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise socket.error()

    def mock_raw():
        return RawMock()

    monkeypatch.setattr(Response, 'raw', property(mock_raw))
    return Response()

def test_claim_c1(mock_response):
    # Given: A socket error occurs during a request
    # When: Calling Response.iter_content()
    # Then: A requests.exceptions.ConnectionError is raised
    with pytest.raises(ConnectionError):
        list(mock_response.iter_content())

def test_iter_content_no_error():
    # Given: No error occurs during a request
    # When: Calling Response.iter_content()
    # Then: No exception is raised
    response = Response()
    response._content = b"test content"
    list(response.iter_content())
    # No exception should be raised

def test_iter_content_other_error(monkeypatch):
    # Given: A different error occurs during a request
    # When: Calling Response.iter_content()
    # Then: The specific error is raised
    class RawMock(object):
        def stream(self, chunk_size, decode_content=None):
            raise ValueError("Other error")

    def mock_raw():
        return RawMock()

    monkeypatch.setattr(Response, 'raw', property(mock_raw))
    response = Response()
    with pytest.raises(ValueError) as excinfo:
        list(response.iter_content())
    assert str(excinfo.value) == "Other error"
