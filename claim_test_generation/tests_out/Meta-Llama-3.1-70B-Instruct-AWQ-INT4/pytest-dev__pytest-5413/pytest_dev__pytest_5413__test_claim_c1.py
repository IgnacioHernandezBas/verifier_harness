import pytest
from pytest import raises

def test_claim_c1(capsys):
    # Given: A LookupError is raised within a pytest.raises context
    # When: str(e) is called on the pytest.raises context variable e
    with raises(LookupError) as e:
        raise LookupError("A\nB\nC")

    # Then: returns 'A\nB\nC'
    assert str(e.value) == "A\nB\nC"

    # Checklist:
    # Test passes with LookupError raised within pytest.raises context
    # str(e) returns the full error message with multiple lines
    # Error message matches the expected format

    # Assertions:
    # str(e) returns the full error message
    assert str(e.value) == "A\nB\nC"
    # error message contains 'A\nB\nC'
    assert "A\nB\nC" in str(e.value)

    # Edge cases:
    # Empty error message
    with raises(LookupError) as e:
        raise LookupError("")
    assert str(e.value) == ""

    # Single-line error message
    with raises(LookupError) as e:
        raise LookupError("A")
    assert str(e.value) == "A"

    # Error message with non-string lines
    with raises(LookupError) as e:
        raise LookupError("A\n1\nC")
    assert str(e.value) == "A\n1\nC"

    # Data setup:
    # Raise LookupError within pytest.raises context
    # Create error message with multiple lines
    with raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    assert str(e.value) == "A\nB\nC"

    # Fixtures:
    # capsys
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
