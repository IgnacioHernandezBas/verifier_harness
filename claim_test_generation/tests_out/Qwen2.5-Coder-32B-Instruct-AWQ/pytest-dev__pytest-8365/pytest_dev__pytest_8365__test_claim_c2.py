# Checklist TODO: Test passes without raising FileNotFoundError.
# Checklist TODO: Directory is created successfully with the given name.
# Checklist TODO: No unexpected errors or warnings are logged.
import pytest

def test_claim_c2(monkeypatch, tmp_path_factory):
    # Given: A username containing backslash (e.g. 'contoso\john_doe') from getpass.getuser()
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")
    
    # When: tmpdir_factory.mktemp('foobar') is called
    temp_dir = tmp_path_factory.mktemp('foobar')
    
    # Then: No FileNotFoundError is raised during directory creation
    assert temp_dir.exists()
    assert temp_dir.is_dir()
