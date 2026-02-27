# Checklist TODO: Test passes without raising FileNotFoundError.
# Checklist TODO: Temporary directory is created successfully.
# Checklist TODO: Environment is correctly mocked with illegal characters in the username.
import pytest
from pytest import monkeypatch

def test_claim_c1(monkeypatch):
    # Given: The username contains illegal characters for directory names
    illegal_username = "os/<:*?;>agnostic"
    monkeypatch.setattr("getpass.getuser", lambda: illegal_username)

    # When: getbasetemp is called
    from _pytest.tmpdir import TempPathFactory
    config = pytest.Config([], None)
    factory = TempPathFactory(config=config, _basetemp=None, _given_basetemp=None)
    p = factory.getbasetemp()

    # Then: FileNotFoundError is not raised
    # Temporary directory is created successfully
    assert p.exists()

    # Environment is correctly mocked with illegal characters in the username
    assert "pytest-of-unknown" in str(p)
