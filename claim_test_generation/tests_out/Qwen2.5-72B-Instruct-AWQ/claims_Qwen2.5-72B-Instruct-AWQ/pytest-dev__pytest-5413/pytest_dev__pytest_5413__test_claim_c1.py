# Checklist TODO: Test must raise a LookupError with a specific multi-line message.
# Checklist TODO: Test must verify the exact string representation of the exception.
# Checklist TODO: Test must ensure the exception type is correctly identified.
import pytest

def test_claim_c1(monkeypatch, capsys):
    # Given: A LookupError is raised within a pytest.raises context
    with pytest.raises(LookupError) as e:
        raise LookupError(
            f"A\n"
            f"B\n"
            f"C"
        )
    
    # When: str(e) is called on the pytest.raises context variable e
    error_message = str(e.value)
    
    # Then: returns 'A\nB\nC'
    assert error_message == 'A\nB\nC'
    
    # Then: e.type is LookupError
    assert e.type is LookupError
    
    # Then: e.match('A\nB\nC')
    e.match('A\nB\nC')

    # Edge case: Test with a single-line LookupError message
    with pytest.raises(LookupError) as e_single:
        raise LookupError("Single line message")
    assert str(e_single.value) == "Single line message"
    assert e_single.type is LookupError
    e_single.match("Single line message")

    # Edge case: Test with no message in the LookupError
    with pytest.raises(LookupError) as e_no_message:
        raise LookupError()
    assert str(e_no_message.value) == ""
    assert e_no_message.type is LookupError
    e_no_message.match("")

    # Edge case: Test with a different exception type, e.g., ValueError
    with pytest.raises(ValueError) as e_value:
        raise ValueError("Value Error Message")
    assert str(e_value.value) == "Value Error Message"
    assert e_value.type is ValueError
    e_value.match("Value Error Message")
