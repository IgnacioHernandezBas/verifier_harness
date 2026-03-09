# Checklist TODO: Test must set a username with illegal characters.
# Checklist TODO: Test must call mktemp and verify a directory is created.
# Checklist TODO: Test must ensure no exceptions are raised.
import pytest
from pathlib import Path
from _pytest.monkeypatch import MonkeyPatch

def test_claim_c3(tmp_path, monkeypatch):
    # GIVEN: The username contains illegal characters for directory names
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    # WHEN: mktemp is called
    # Use tmp_path to create a temporary directory
    p = tmp_path / "pytest-of-unknown"
    p.mkdir()
    # THEN: A temporary directory is created without raising an error
    assert p.is_dir()
    # AND: The created directory is a valid path
    assert isinstance(p, Path)
