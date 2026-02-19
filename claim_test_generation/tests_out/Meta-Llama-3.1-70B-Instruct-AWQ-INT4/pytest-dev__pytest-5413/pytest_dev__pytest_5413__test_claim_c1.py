import pytest
from pytest import raises

def test_claim_c1(capsys):
    # Given: A LookupError is raised with a multi-line error message
    # When: calling str() on the pytest.raises context variable
    # Then: returns the full error message, including all lines

    # Checklist: Test passes with multi-line error message
    with raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    captured = capsys.readouterr()
    assert "A\nB\nC" in str(e.value)

    # Checklist: Test fails with single-line error message
    with raises(LookupError) as e:
        raise LookupError("Single line")
    captured = capsys.readouterr()
    assert "Single line" in str(e.value)

    # Checklist: Test handles non-LookupError exceptions correctly
    with raises(ValueError) as e:
        raise ValueError("Non-LookupError exception")
    captured = capsys.readouterr()
    assert "Non-LookupError exception" in str(e.value)

    # Edge case: Single-line error message
    with raises(LookupError) as e:
        raise LookupError("Single line")
    captured = capsys.readouterr()
    assert "Single line" in str(e.value)

    # Edge case: Error message with non-string lines
    with raises(LookupError) as e:
        raise LookupError(["A", "B", "C"])
    captured = capsys.readouterr()
    assert "['A', 'B', 'C']" in str(e.value)

    # Edge case: Non-LookupError exception
    with raises(ValueError) as e:
        raise ValueError("Non-LookupError exception")
    captured = capsys.readouterr()
    assert "Non-LookupError exception" in str(e.value)
