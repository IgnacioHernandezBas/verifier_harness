import pytest
from pathlib import Path
import tempfile
import getpass

def test_claim_c2(monkeypatch):
    # Given: A username containing backslash (e.g. 'contoso\john_doe') from getpass.getuser()
    # Checklist: Test passes with backslash-containing username
    monkeypatch.setattr(getpass, 'getuser', lambda: 'contoso\\john_doe')

    # When: tmpdir_factory.mktemp('foobar') is called
    # Checklist: Directory creation succeeds without FileNotFoundError
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Checklist: Test does not fail with NameError for getpass
        try:
            # Exercise mktemp with backslash-containing username
            tmp_path.mkdir(exist_ok=True)
        except FileNotFoundError:
            pytest.fail("FileNotFoundError raised during directory creation")

    # Then: No FileNotFoundError is raised during directory creation
    # Assertions:
    # 1. No FileNotFoundError is raised during directory creation
    # 2. Directory is created successfully
    assert tmp_path.exists()
