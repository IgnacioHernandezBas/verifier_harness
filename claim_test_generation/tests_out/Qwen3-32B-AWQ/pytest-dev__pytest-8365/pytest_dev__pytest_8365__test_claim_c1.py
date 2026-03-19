# Checklist TODO: Sanitized username appears in directory path
# Checklist TODO: Directory created with 0o777 permissions
# Checklist TODO: Handles invalid characters across platforms
import pytest
from _pytest.tmpdir import TempPathFactory
from pytest import TempPathFactory as TPF  # type: ignore


def test_claim_c1(tmp_path_factory: TempPathFactory, monkeypatch):
    # GIVEN: A username with backslash
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")
    # Clear cached values to force recomputation
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # WHEN: getbasetemp is called
    path = tmp_path_factory.getbasetemp()

    # THEN: 1. Sanitized username appears in directory path
    # Note: The sanitized username replaces backslash with underscore
    assert "pytest-of-contoso_john_doe" in str(path)
    # THEN: 2. Directory exists
    assert path.exists()
    # THEN: 3. Directory has 0o777 (511) permissions
    assert oct(path.stat().st_mode & 0o777) == "0o777"
