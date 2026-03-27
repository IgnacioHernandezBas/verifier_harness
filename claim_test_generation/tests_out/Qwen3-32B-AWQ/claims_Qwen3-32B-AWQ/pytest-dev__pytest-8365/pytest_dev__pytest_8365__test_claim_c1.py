import pytest

def test_claim_c1(tmp_path_factory, monkeypatch):
    # Mock username contains backslash via monkeypatch
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")
    # Clear cached basetemp values
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)
    
    # getbasetemp() produces path with sanitized username
    basetemp = tmp_path_factory.getbasetemp()
    
    # Assertion verifies absence of invalid characters in final path
    assert "pytest-of-contoso_john_doe" in str(basetemp)
    assert basetemp.exists()
    assert "\\" not in str(basetemp)
