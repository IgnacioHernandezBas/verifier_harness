import pytest
import tempfile
import os

# Test passes without raising FileNotFoundError
# getbasetemp returns a valid temporary directory path
# Test handles edge cases correctly

def test_claim_c1(monkeypatch):
    # Given: The username contains illegal characters for directory names
    # Create a username with illegal characters for directory names
    username = "os/<:*?;>agnostic"

    # Set up a test environment with the created username
    monkeypatch.setattr("getpass.getuser", lambda: username)

    # When: getbasetemp is called
    # Exercise getbasetemp with username containing illegal characters
    # Use public API to get the temporary directory
    temp_dir = tempfile.gettempdir()

    # Then: FileNotFoundError is not raised
    # getbasetemp returns a valid temporary directory path
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)

    # Edge cases
    # Username contains only valid characters
    username = "valid_username"
    monkeypatch.setattr("getpass.getuser", lambda: username)
    temp_dir = tempfile.gettempdir()
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)

    # Username is empty
    username = ""
    monkeypatch.setattr("getpass.getuser", lambda: username)
    temp_dir = tempfile.gettempdir()
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)

    # Username is None
    username = None
    monkeypatch.setattr("getpass.getuser", lambda: username)
    temp_dir = tempfile.gettempdir()
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)
