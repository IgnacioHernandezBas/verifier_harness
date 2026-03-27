# Checklist TODO: Mock username contains invalid directory chars
# Checklist TODO: getbasetemp() returns Path object
# Checklist TODO: Resulting path exists and is accessible
import pytest
from pathlib import Path

def test_claim_c2(tmp_path_factory, monkeypatch):
    # GIVEN: Mock username with illegal directory characters
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    # Reset cached values to force recomputation
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # WHEN: Call getbasetemp
    result = tmp_path_factory.getbasetemp()

    # THEN: Verify the returned path is valid
    assert result.is_dir()  # Check if directory exists
    assert "pytest-of-" in str(result)  # Check for expected path structure
    assert result.exists()  # Ensure path is accessible
