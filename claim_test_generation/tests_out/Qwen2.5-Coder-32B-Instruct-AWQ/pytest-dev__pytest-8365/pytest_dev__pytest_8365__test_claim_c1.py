import pytest
from pytest import monkeypatch

def test_claim_c1(monkeypatch):
    # Given: A username containing backslash (e.g. 'contoso\john_doe') from getpass.getuser()
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")

    # When: getbasetemp() is called during tmpdir_factory initialization
    from _pytest.tmpdir import TempPathFactory
    tmp_path_factory = TempPathFactory(config=None, _basetemp=None, _given_basetemp=None)
    p = tmp_path_factory.getbasetemp()

    # Then: The directory 'pytest-of-<sanitized_user>' is successfully created without invalid characters in the path
    # Directory name is sanitized correctly.
    assert "pytest-of-contoso_john_doe" in str(p)

    # No errors occur during directory creation.
    # Directory is located in the system's temp directory.
    import tempfile
    assert str(p).startswith(tempfile.gettempdir())
