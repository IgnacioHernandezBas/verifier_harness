# Checklist TODO: mktemp creates directory without raising errors
# Checklist TODO: Handles invalid username characters in path
# Checklist TODO: Directory exists with sanitized naming
import pytest

def test_claim_c3(tmpdir, monkeypatch):
    # Given: username with illegal characters for directory names
    monkeypatch.setattr("getpass.getuser", lambda: "john_doe!@#")
    
    # When: tmpdir is created (implicitly using mktemp mechanisms)
    # Then: No exception raised and directory exists
    assert tmpdir.exists()
    
    # Check that the path contains the sanitized username segment
    # (assuming invalid characters are replaced with safe equivalents)
    assert "john_doe" in str(tmpdir)
