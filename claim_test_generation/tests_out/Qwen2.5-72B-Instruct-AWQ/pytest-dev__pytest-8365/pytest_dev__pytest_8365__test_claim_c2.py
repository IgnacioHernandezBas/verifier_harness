# Checklist TODO: Mock os.environ to simulate illegal username.
# Checklist TODO: Assert getbasetemp returns a valid path.
# Checklist TODO: Ensure path is a directory and does not contain illegal characters.
import pytest
from pathlib import Path

def test_claim_c2(monkeypatch, tmpdir):
    # GIVEN: The username contains illegal characters for directory names
    monkeypatch.setattr("os.environ", {"USERPROFILE": "C:/Users/os/<:*?;>agnostic"})
    
    # WHEN: getbasetemp is called
    from _pytest.pathlib import getbasetemp
    p = getbasetemp()

    # THEN: A valid temporary directory path is returned
    assert p is not None
    assert isinstance(p, Path)
    assert p.exists()
    assert p.is_dir()

    # Ensure path is a directory and does not contain illegal characters
    assert "pytest-of-unknown" in str(p)
    assert all(c not in str(p) for c in "<:*?;>")
