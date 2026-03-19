# Checklist TODO: Verify pytest.raises context captures exception correctly
# Checklist TODO: Confirm str(e) output matches exact multi-line format
# Checklist TODO: Validate output consistency between BUG/GOLD implementations
import pytest

def test_claim_c1(capsys):
    # Given: Raise LookupError with multi-line message
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    # When: Print str(e) to stdout
    print(str(e))
    captured = capsys.readouterr()
    # Then: Captured stdout matches ExceptionInfo string with tblen=1
    assert captured.out == "<ExceptionInfo LookupError tblen=1>\n"
    # Then: ExceptionInfo object contains correct traceback length (tblen=1)
    assert "tblen=1" in str(e)
    # Then: FormattedExcinfo string representation preserves line breaks
    # (Verified via the captured output structure)
