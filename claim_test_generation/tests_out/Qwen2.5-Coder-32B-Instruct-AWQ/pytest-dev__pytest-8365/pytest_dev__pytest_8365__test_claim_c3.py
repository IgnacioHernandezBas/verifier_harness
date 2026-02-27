# Checklist TODO: Test passes without raising an error
# Checklist TODO: Temporary directory is created successfully
# Checklist TODO: Directory name is sanitized appropriately
import pytest

def test_claim_c3(monkeypatch, tmp_path_factory):
    # Given: The username contains illegal characters for directory names
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    
    # When: mktemp is called
    p = tmp_path_factory.mktemp("test")
    
    # Then: A temporary directory is created without raising an error
    assert p.exists()
    assert "pytest-of-unknown" in str(p)
