# Checklist TODO: Test raises ConnectionError on socket error
# Checklist TODO: Wrapped error matches original OSError type
# Checklist TODO: Fails without proper exception handling
import pytest
from requests.models import Response
from requests.exceptions import ConnectionError

def test_claim_c1():
    # GIVEN: A socket error occurs during the read operation in the response content streaming.
    class MockRaw:
        def stream(self, *args, **kwargs):
            raise OSError("Socket error")
    
    response = Response()
    response.raw = MockRaw()
    
    # WHEN: self.raw.stream(chunk_size, decode_content=True) is called in the iter_content method
    # THEN: A requests.exceptions.ConnectionError is raised.
    with pytest.raises(ConnectionError):
        list(response.iter_content())
