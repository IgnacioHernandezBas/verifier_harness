import pytest
from pytest import raises

def test_claim_c2(capsys):
    # Given: A LookupError is raised with a multi-line error message
    # When: calling str() on the pytest.raises context variable
    with raises(LookupError) as e:
        raise LookupError("A\nB\nC")

    # Then: returns a string containing all lines of the error message, not just 'A'
    assert "A\nB\nC" in str(e.value)

    # Checklist: Test passes with multi-line error message
    assert "A" not in str(e.value).splitlines()[0]

    # Checklist: Test fails with single-line error message
    with raises(LookupError) as e_single_line:
        raise LookupError("A")
    assert "A" in str(e_single_line.value).splitlines()[0]

    # Checklist: Test handles non-LookupError exceptions correctly
    with raises(ValueError) as e_value_error:
        raise ValueError("A\nB\nC")
    assert "A\nB\nC" in str(e_value_error.value)

    # Edge case: Single-line error message
    with raises(LookupError) as e_single_line:
        raise LookupError("A")
    assert "A" in str(e_single_line.value).splitlines()[0]

    # Edge case: Error message with non-string lines
    with raises(LookupError) as e_non_string_lines:
        raise LookupError(["A", "B", "C"])
    assert "['A', 'B', 'C']" in str(e_non_string_lines.value)

    # Edge case: Non-LookupError exception
    with raises(ValueError) as e_value_error:
        raise ValueError("A\nB\nC")
    assert "A\nB\nC" in str(e_value_error.value)
