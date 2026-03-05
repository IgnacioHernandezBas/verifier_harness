# Checklist TODO: Test must use tmpdir to create a temporary directory.
# Checklist TODO: Test must use monkeypatch to set the username environment variable.
# Checklist TODO: Test must verify the directory is created without errors.
import pytest

def test_claim_c3(tmpdir, monkeypatch):
    # Given: The username contains illegal characters for directory names
    illegal_username = "os/<:*?;>agnostic"
    monkeypatch.setenv("USER", illegal_username)

    # When: mktemp is called
    temp_dir = tmpdir.mkdir("test_dir")

    # Then: A temporary directory is created without raising an error
    assert temp_dir.isdir(), "Temporary directory is created without error."

    # Then: Temporary directory path does not contain illegal characters
    assert all(c not in str(temp_dir) for c in "<>:*?|"), "Temporary directory path does not contain illegal characters."

    # Then: Temporary directory is a valid directory object
    assert isinstance(temp_dir, pytest.pytest._Path), "Temporary directory is a valid directory object."

    # Edge cases
    # Username with leading/trailing spaces
    monkeypatch.setenv("USER", "  leading_space")
    temp_dir_leading_space = tmpdir.mkdir("test_dir_leading_space")
    assert temp_dir_leading_space.isdir(), "Temporary directory with leading space is created without error."

    # Username with only illegal characters
    monkeypatch.setenv("USER", "<>:*?|")
    temp_dir_illegal_only = tmpdir.mkdir("test_dir_illegal_only")
    assert temp_dir_illegal_only.isdir(), "Temporary directory with only illegal characters is created without error."

    # Username with maximum allowed length plus one illegal character
    max_length_username = "a" * 255 + "<"
    monkeypatch.setenv("USER", max_length_username)
    temp_dir_max_length = tmpdir.mkdir("test_dir_max_length")
    assert temp_dir_max_length.isdir(), "Temporary directory with max length plus one illegal character is created without error."
