# Checklist TODO: Test passes with illegal characters in username.
# Checklist TODO: Directory path is sanitized correctly.
# Checklist TODO: No errors during directory creation.
import pytest

def test_claim_c2(monkeypatch, tmp_path_factory):
    # Given: The username returned by `getpass.getuser()` contains illegal characters for directory names, such as a backslash.
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    # _basetemp / _given_basetemp are cached / set in parallel runs, patch them
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # When: The `getbasetemp` method of `TempPathFactory` is called.
    p = tmp_path_factory.getbasetemp()

    # Then: The `basetemp` directory should be created without illegal characters in its path.
    # The basetemp directory path does not contain illegal characters.
    assert not any(char in str(p) for char in "/<>:*?;|")

    # The basetemp directory is created successfully.
    assert p.exists()

    # The basetemp directory path is as expected after sanitization.
    assert "pytest-of-unknown" in str(p)
