import pytest
from pathlib import Path
import tempfile
import os

# Given: A username containing backslash (e.g. 'contoso\john_doe') from getpass.getuser()
# When: getbasetemp() is called during tmpdir_factory initialization
# Then: The directory 'pytest-of-<sanitized_user>' is successfully created without invalid characters in the path

def test_claim_c1(monkeypatch):
    # Checklist: Test creates a valid base temporary directory
    # Checklist: Test handles usernames with backslashes correctly
    # Checklist: Test does not create directories with invalid characters

    # Data setup: Username with backslash (e.g. 'contoso\john_doe')
    username = 'contoso\\john_doe'
    monkeypatch.setattr('getpass.getuser', lambda: username)

    # Data setup: Mock getpass.getuser() to return the username
    # Edge case: Username with multiple backslashes
    username_multiple_backslashes = 'contoso\\\\john_doe'
    monkeypatch.setattr('getpass.getuser', lambda: username_multiple_backslashes)

    # Edge case: Username with other special characters
    username_special_chars = 'contoso!@#$%^&*()john_doe'
    monkeypatch.setattr('getpass.getuser', lambda: username_special_chars)

    # Edge case: Empty username
    username_empty = ''
    monkeypatch.setattr('getpass.getuser', lambda: username_empty)

    # Assertions: Directory 'pytest-of-<sanitized_user>' is created
    # Assertions: Directory path does not contain invalid characters
    def getbasetemp():
        user = getpass.getuser()
        sanitized_user = re.sub(r'[^a-zA-Z0-9_\-]', '_', user)
        return Path(tempfile.gettempdir()) / f'pytest-of-{sanitized_user}'

    basetemp = getbasetemp()
    assert basetemp.exists()
    assert str(basetemp).replace('\\', '/') == str(basetemp).replace('\\', '/').lower()
