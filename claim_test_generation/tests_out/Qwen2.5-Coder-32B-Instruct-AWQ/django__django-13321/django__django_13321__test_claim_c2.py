# Checklist TODO: Function handles invalid base64 data correctly.
# Checklist TODO: Returns empty dictionary as expected.
# Checklist TODO: No exceptions are raised during execution.
import pytest
from django.contrib.sessions.backends.base import SessionBase

def test_claim_c2():
    # Given: Session data that fails base64 decoding in _legacy_decode
    invalid_base64_data = 'invalid:base64:string'
    empty_string_data = ''
    non_string_data = 12345

    # When: _legacy_decode is called with invalid data
    session = SessionBase()

    # Then: Returns empty dictionary as expected.
    # No exceptions are raised during execution.
    result_invalid = session._legacy_decode(invalid_base64_data)
    assert isinstance(result_invalid, dict)
    assert len(result_invalid) == 0

    result_empty = session._legacy_decode(empty_string_data)
    assert isinstance(result_empty, dict)
    assert len(result_empty) == 0

    result_non_string = session._legacy_decode(non_string_data)
    assert isinstance(result_non_string, dict)
    assert len(result_non_string) == 0
