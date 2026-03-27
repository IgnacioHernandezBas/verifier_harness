# Checklist TODO: Mock username contains illegal path chars
# Checklist TODO: tmpdir_factory.mktemp() completes without exception
# Checklist TODO: Generated path avoids filename collision
import pytest

def test_claim_c1(tmp_path_factory, monkeypatch):
    # Given: Mock username with illegal characters for directory names
    monkeypatch.setattr("getpass.getuser", lambda: "contoso\\john_doe")
    # Reset cached base temp paths to force recalculation
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # When/Then: Creating temporary directory structure should not raise FileNotFoundError
    # 1. Base temporary directory creation should succeed
    base_temp = tmp_path_factory.getbasetemp()
    assert "pytest-of-contoso" in str(base_temp).replace("\\", "-")

    # 2. Subdirectory creation via mktemp should succeed
    temp_dir = tmp_path_factory.mktemp("foobar")
    assert temp_dir.exists()
    assert "foobar" in str(temp_dir)
