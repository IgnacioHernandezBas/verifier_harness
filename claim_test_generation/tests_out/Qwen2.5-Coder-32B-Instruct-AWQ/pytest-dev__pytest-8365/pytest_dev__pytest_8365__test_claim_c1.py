# Checklist TODO: Test passes without raising FileNotFoundError.
# Checklist TODO: Temporary directory is created successfully.
# Checklist TODO: Mocked username is correctly handled.
import pytest
from pytest import monkeypatch

def test_claim_c1(monkeypatch):
    # Given: The username returned by getpass.getuser() contains illegal characters for directory names, e.g., 'contoso\john_doe'.
    monkeypatch.setattr('getpass.getuser', lambda: 'contoso\\john_doe')
    
    # When: tmpdir_factory.mktemp('foobar') is called
    from _pytest.tmpdir import TempdirFactory
    tmpdir_factory = TempdirFactory(basetemp=None)
    temp_dir = tmpdir_factory.mktemp('foobar')
    
    # Then: No FileNotFoundError is raised.
    # Temporary directory is created successfully.
    assert temp_dir.exists()
    
    # Mocked username is correctly handled.
    assert 'contoso' in str(temp_dir)
    assert 'john_doe' in str(temp_dir)
