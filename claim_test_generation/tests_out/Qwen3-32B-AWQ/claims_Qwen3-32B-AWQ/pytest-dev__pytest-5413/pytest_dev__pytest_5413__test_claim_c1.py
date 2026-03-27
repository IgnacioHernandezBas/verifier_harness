# Checklist TODO: Test verifies str(e) returns message, not type/path
# Checklist TODO: Multi-line message is preserved in output
# Checklist TODO: Assertion excludes forbidden substrings (type, path)
import pytest

def test_claim_c1():
    # Given: Raise LookupError with multi-line message
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    
    # When: str(e) is called
    result = str(e)
    
    # Then: Verify output contains ExceptionInfo format, not message or path
    assert result.startswith("<ExceptionInfo ")
    assert "LookupError" in result  # Part of ExceptionInfo format
    assert "tblen" in result  # Confirms ExceptionInfo structure
    assert "A\nB\nC" not in result  # Message not present
    assert __file__ not in result  # File path not present
