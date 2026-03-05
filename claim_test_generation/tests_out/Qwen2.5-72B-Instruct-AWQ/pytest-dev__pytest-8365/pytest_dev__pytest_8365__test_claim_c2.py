import pytest
from pathlib import Path

def test_claim_c2(monkeypatch):
    # GIVEN: The username contains illegal characters for directory names
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    
    # WHEN: getbasetemp is called
    from _pytest.tmpdir import getbasetemp
    p = getbasetemp()
    
    # THEN: A valid temporary directory path is returned
    assert isinstance(p, Path), "getbasetemp should return a Path object"
    assert p.is_dir(), "The returned path should be a valid directory"
    assert "pytest-of-unknown" in str(p), "The returned path should contain 'pytest-of-unknown'"
    
    # Test must simulate an environment with an illegal username.
    # Test must verify the returned path is valid and not empty.
    # Test must reset the environment after execution.
