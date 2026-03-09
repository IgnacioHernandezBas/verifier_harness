# Checklist TODO: Mock getpass.getuser() with illegal characters in username
# Checklist TODO: Call tmpdir_factory.mktemp() and ensure no FileNotFoundError
# Checklist TODO: Verify the temporary directory is created and accessible
import pytest

def test_claim_c1(tmpdir_factory, monkeypatch):
    # GIVEN: The username returned by getpass.getuser() contains illegal characters for directory names, e.g., 'contoso\john_doe'.
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")

    # WHEN: tmpdir_factory.mktemp('foobar') is called
    try:
        temp_dir = tmpdir_factory.mktemp('foobar')
    except FileNotFoundError as e:
        pytest.fail(f"FileNotFoundError was raised: {e}")

    # THEN: No FileNotFoundError is raised.
    # Verify the temporary directory is created and accessible
    assert temp_dir.isdir(), "The temporary directory was not created successfully"
