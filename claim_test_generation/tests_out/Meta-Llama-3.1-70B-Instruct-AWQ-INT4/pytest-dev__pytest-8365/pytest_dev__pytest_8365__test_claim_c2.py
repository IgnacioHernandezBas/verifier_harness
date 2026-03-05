import pytest
from _pytest.tmpdir import TempPathFactory
import getpass
import os

def test_claim_c2(monkeypatch):
    # Given: The username returned by `getpass.getuser()` contains illegal characters for directory names, such as a backslash.
    # When: The `getbasetemp` method of `TempPathFactory` is called.
    # Then: The `basetemp` directory should be created without illegal characters in its path.

    # Checklist: Test passes with a username containing illegal characters
    # Checklist: The created directory path does not contain illegal characters
    # Checklist: The test fails if the username is not properly sanitized

    # Data setup: Mock getpass.getuser() to return a username with illegal characters
    monkeypatch.setattr(getpass, "getuser", lambda: "os/<:*?;>agnostic")

    # Data setup: Create a TempPathFactory instance with the mocked username
    factory = TempPathFactory(basetemp="basetemp", trace=None)

    # Exercise TempPathFactory with monkeypatched getpass.getuser()
    basetemp = factory.getbasetemp()

    # Assertions: The basetemp directory is created without illegal characters in its path
    assert "pytest-of-unknown" in str(basetemp)

    # Assertions: The created directory exists and is a valid path
    assert os.path.exists(basetemp)
    assert os.path.isdir(basetemp)

    # Edge cases: Username contains a backslash
    monkeypatch.setattr(getpass, "getuser", lambda: "os\\<:*?;>agnostic")
    factory = TempPathFactory(basetemp="basetemp", trace=None)
    basetemp = factory.getbasetemp()
    assert "pytest-of-unknown" in str(basetemp)
    assert os.path.exists(basetemp)
    assert os.path.isdir(basetemp)

    # Edge cases: Username contains a forward slash
    monkeypatch.setattr(getpass, "getuser", lambda: "os/<:*?;>agnostic")
    factory = TempPathFactory(basetemp="basetemp", trace=None)
    basetemp = factory.getbasetemp()
    assert "pytest-of-unknown" in str(basetemp)
    assert os.path.exists(basetemp)
    assert os.path.isdir(basetemp)

    # Edge cases: Username is empty
    monkeypatch.setattr(getpass, "getuser", lambda: "")
    factory = TempPathFactory(basetemp="basetemp", trace=None)
    basetemp = factory.getbasetemp()
    assert "pytest-of-unknown" in str(basetemp)
    assert os.path.exists(basetemp)
    assert os.path.isdir(basetemp)
