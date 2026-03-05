# Checklist TODO: Test passes without raising FileNotFoundError.
# Checklist TODO: Temporary directory is created successfully.
# Checklist TODO: No unexpected errors are raised.
import pytest

def test_claim_c1(monkeypatch, tmp_path_factory):
    # Given: The username returned by `getpass.getuser()` contains illegal characters for directory names, such as a backslash.
    monkeypatch.setattr("getpass.getuser", lambda: "os\\<:*?;>agnostic")
    # _basetemp / _given_basetemp are cached / set in parallel runs, patch them
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # When: The `mktemp` method of `TempPathFactory` is called with a valid `basename` and `numbered` parameter.
    try:
        p = tmp_path_factory.mktemp("valid_basename", numbered=True)
    except FileNotFoundError:
        pytest.fail("FileNotFoundError should not be raised")

    # Then: A `FileNotFoundError` should not be raised.
    # Temporary directory is created successfully.
    assert p.exists()
    # No unexpected errors are raised.
