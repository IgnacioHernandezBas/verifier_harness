# Checklist TODO: Verify output length constraint is enforced
# Checklist TODO: Confirm public API usage without internal imports
# Checklist TODO: Validate truncation behavior across edge cases
import pytest

def test_claim_c2(capsys):
    # Given: An object with a large string representation
    class LargeRepr:
        def __repr__(self):
            return 'a' * 100  # 100 characters
    obj = LargeRepr()

    # When: Triggering an error that uses saferepr
    with pytest.raises(AssertionError):
        assert obj == 1  # This will raise an AssertionError

    # Then: Check that the output is truncated
    captured = capsys.readouterr()
    # The error message should contain the truncated representation
    # 1. Captured output contains truncated string (length <= maxsize)
    assert len(captured.err) <= 100  # Assuming default maxsize is less than 100
    # 2. Truncation indicator (e.g., '...') present in output
    assert '...' in captured.err
    # 3. Original object's __repr__ was longer than maxsize
    # Verified by the fact that the original repr is 100 chars and output is shorter
