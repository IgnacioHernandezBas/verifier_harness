# Checklist TODO: Test verifies _legacy_decode returns empty dict on invalid data
# Checklist TODO: No exceptions propagate during test execution
# Checklist TODO: Test validates backward compatibility behavior
import pytest
import sys
import types

def test_claim_c2(monkeypatch):
    # GIVEN: Add repo path to sys.path and mock missing dependencies
    repo_path = "/fs/nexus-scratch/ihbas/repos_claim_cache/django__django/35b03788b0607c1f8d2b64e4fa9e1669b0907ea4"
    monkeypatch.syspath_prepend(repo_path)
    sys.modules["asgiref"] = types.ModuleType("asgiref")

    # WHEN: Import target module and exercise _legacy_decode with invalid data
    try:
        from django.contrib.sessions.backends import base
        session = base.SessionBase()
        invalid_data = "invalid=="
        result = session._legacy_decode(invalid_data)
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")

    # THEN: Verify returns empty dict without exceptions
    assert result == {}
    # Edge case: Empty string
    assert session._legacy_decode("") == {}
    # Edge case: Non-string input (None)
    assert session._legacy_decode(None) == {}
