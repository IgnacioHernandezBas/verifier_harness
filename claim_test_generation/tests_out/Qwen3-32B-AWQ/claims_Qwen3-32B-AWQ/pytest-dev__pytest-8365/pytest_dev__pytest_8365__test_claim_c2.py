# Checklist TODO: No exception raised for special-char usernames
# Checklist TODO: Directory created with pytest-of- prefix
# Checklist TODO: Path sanitization handles Windows/Posix correctly
import pytest

def test_claim_c2(tmp_path_factory, monkeypatch):
    # GIVEN: Mock username with backslash
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")
    # Reset cached basetemp to force recomputation
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # WHEN: Attempt to generate base temporary directory path
    # (this triggers path sanitization and directory creation logic)
    try:
        basetemp = tmp_path_factory.getbasetemp()
    except FileNotFoundError as e:
        # THEN: Ensure no FileNotFoundError is raised
        pytest.fail(f"Unexpected FileNotFoundError: {e}")

    # THEN: Verify directory path contains 'pytest-of-' with sanitized username
    # Note: Backslash in username should be replaced with underscore or removed
    assert "pytest-of-contoso" in str(basetemp).replace("\\", "/")
    assert "contoso_john_doe" in str(basetemp).replace("\\", "/")
