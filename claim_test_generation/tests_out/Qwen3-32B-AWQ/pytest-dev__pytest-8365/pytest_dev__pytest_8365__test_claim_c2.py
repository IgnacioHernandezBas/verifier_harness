# Checklist TODO: Username is properly mocked with backslash character
# Checklist TODO: mktemp() call completes without FileNotFoundError
# Checklist TODO: Generated path uses safe directory separators (_ instead of \)
import pytest

def test_claim_c2(tmp_path_factory, monkeypatch):
    # GIVEN: Mock username with backslash
    mock_user = "contoso\\john_doe"
    monkeypatch.setattr("getpass.getuser", lambda: mock_user)
    # Reset cached basetemp values
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # WHEN: Call getbasetemp (which uses mktemp internally)
    try:
        path = tmp_path_factory.getbasetemp()
    except FileNotFoundError as e:
        # THEN: Ensure FileNotFoundError is not raised
        pytest.fail(f"FileNotFoundError raised unexpectedly: {e}")

    # THEN: Check generated path uses safe characters
    safe_user_part = mock_user.replace("\\", "_")
    assert safe_user_part in str(path), f"Expected '{safe_user_part}' in path, got {path}"
    # THEN: Verify directory exists
    assert path.exists(), f"Directory {path} was not created"
