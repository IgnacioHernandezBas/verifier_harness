# Checklist TODO: Test passes with illegal characters in username.
# Checklist TODO: Temporary directory path is valid and accessible.
# Checklist TODO: No errors are raised during getbasetemp execution.
import pytest

def test_claim_c2(monkeypatch, tmp_path_factory):
    # Given: The username contains illegal characters for directory names
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    # _basetemp / _given_basetemp are cached / set in parallel runs, patch them
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # When: getbasetemp is called
    p = tmp_path_factory.getbasetemp()

    # Then: A valid temporary directory path is returned
    assert "pytest-of-unknown" in str(p)
    assert p.exists()
    assert p.is_dir()
