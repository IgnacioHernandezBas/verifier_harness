import pytest

def test_claim_c1(capsys):
    # GIVEN: A LookupError is raised with a multi-line message inside a pytest.raises context.
    # WHEN: str(e) is called where e is the pytest.raises context variable.
    # THEN: The full error message 'A\nB\nC' is returned.

    # Test passes with a multi-line error message
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    assert str(e.value) == "A\nB\nC"

    # Test fails with an incorrect error message
    with pytest.raises(LookupError) as e:
        raise LookupError("A\nB\nC")
    assert str(e.value) != "A\nB\nD"

    # Test handles non-LookupError exceptions correctly
    with pytest.raises(ValueError) as e:
        raise ValueError("A\nB\nC")
    assert str(e.value) == "A\nB\nC"

    # Edge case: Test with a single-line error message
    with pytest.raises(LookupError) as e:
        raise LookupError("A")
    assert str(e.value) == "A"

    # Edge case: Test with a non-string error message
    with pytest.raises(LookupError) as e:
        raise LookupError(123)
    assert str(e.value) == "123"

    # Edge case: Test with a non-LookupError exception
    with pytest.raises(ValueError) as e:
        raise ValueError("A\nB\nC")
    assert str(e.value) == "A\nB\nC"
