# Checklist TODO: Test passes without raising FileNotFoundError.
# Checklist TODO: Temporary directory is created successfully.
# Checklist TODO: Mocked username is correctly handled.
import pytest

def test_claim_c1(monkeypatch, tmpdir_factory):
    # Given: The username returned by getpass.getuser() contains illegal characters for directory names, e.g., 'contoso\john_doe'.
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")
    
    # When: tmpdir_factory.mktemp('foobar') is called
    temp_dir = tmpdir_factory.mktemp('foobar')
    
    # Then: No FileNotFoundError is raised.
    # Temporary directory is created successfully.
    assert temp_dir.exists()
    
    # Mocked username is correctly handled.
    assert "pytest-of-contoso" in str(temp_dir)
