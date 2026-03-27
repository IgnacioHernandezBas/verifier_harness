# Checklist TODO: Test must mock getuser to control input.
# Checklist TODO: Test must verify sanitized directory name.
# Checklist TODO: Test must ensure path validity and existence.
import pytest
from pathlib import Path
from _pytest.monkeypatch import MonkeyPatch
from _pytest.pathlib import TempPathFactory

def test_claim_c1(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    # GIVEN: Mock getuser to return 'contoso\john_doe'
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")

    # WHEN: Initialize tmpdir_factory with mocked getuser
    tmpdir_factory = TempPathFactory(given_basetemp=tmp_path)

    # THEN: Directory 'pytest-of-<sanitized_user>' is created
    basetemp = tmpdir_factory.getbasetemp()
    assert "pytest-of-unknown" in str(basetemp)

    # THEN: Path does not contain illegal characters
    assert all(c not in str(basetemp) for c in r'<>:"/\|?*')

    # THEN: getbasetemp returns a valid Path object
    assert isinstance(basetemp, Path)
    assert basetemp.exists()
