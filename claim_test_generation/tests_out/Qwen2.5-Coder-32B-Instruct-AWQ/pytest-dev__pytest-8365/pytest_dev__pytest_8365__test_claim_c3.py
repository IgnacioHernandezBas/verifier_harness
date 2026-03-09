import pytest
from pytest import monkeypatch
from pathlib import Path

def test_claim_c3(tmpdir):
    # Given: The username contains illegal characters for directory names
    illegal_username = "os/<:*?;>agnostic"
    monkeypatch.setattr("getpass.getuser", lambda: illegal_username)

    # When: mktemp is called
    from _pytest.tmpdir import mktemp
    temp_dir = mktemp(basename="pytest-of-unknown", rootdir=tmpdir)

    # Then: A temporary directory is created without raising an error
    # mktemp creates a directory successfully
    assert temp_dir.exists()
    # No errors are raised during directory creation
    # Directory path is valid and accessible
    assert temp_dir.is_dir()
    assert "pytest-of-unknown" in str(temp_dir)
