# Checklist TODO: Monkeypatch username with invalid characters
# Checklist TODO: Call getbasetemp() without exception handling
# Checklist TODO: Verify no FileNotFoundError raised during execution
import pytest

def test_claim_c1(tmp_path_factory, monkeypatch):
    # GIVEN: Username contains illegal directory characters
    monkeypatch.setattr("getpass.getuser", lambda: "os/<:*?;>agnostic")
    # Reset cached values to force recomputation
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # WHEN: Call getbasetemp without exception handling
    # THEN: No FileNotFoundError raised, path exists
    path = tmp_path_factory.getbasetemp()
    assert path.exists()
