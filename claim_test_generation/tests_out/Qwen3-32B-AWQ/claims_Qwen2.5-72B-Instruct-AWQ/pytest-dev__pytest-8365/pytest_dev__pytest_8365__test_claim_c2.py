# Checklist TODO: Sanitized username used in path creation
# Checklist TODO: Directory created without invalid characters
# Checklist TODO: Test validates public API behavior without implementation details
import pytest

def test_claim_c2(tmp_path_factory, monkeypatch):
    # GIVEN: Username with illegal characters
    monkeypatch.setattr("getpass.getuser", lambda: "john\\doe")
    # Reset cached values to force recomputation
    monkeypatch.setattr(tmp_path_factory, "_basetemp", None)
    monkeypatch.setattr(tmp_path_factory, "_given_basetemp", None)

    # WHEN: Call getbasetemp
    with pytest.warns(None) as warning_record:  # THEN: No warnings raised
        basetemp = tmp_path_factory.getbasetemp()

    # THEN: 1. Path contains no backslashes
    assert "\\" not in str(basetemp), f"Path contains invalid characters: {basetemp}"
    # THEN: 2. Directory is created successfully
    assert basetemp.exists(), f"Directory not created: {basetemp}"
    # THEN: 3. No deprecation warnings
    assert not warning_record.list, f"Unexpected warnings: {warning_record.list}"
