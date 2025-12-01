from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule6_detects_broad_exception(repo_root: Path, run_rule) -> None:
    old = """
def fetch(data):
    if data is None:
        raise ValueError("data required")
    return data
"""
    new = """
def fetch(data):
    try:
        return data["value"]
    except Exception:
        raise Exception("failed")
"""
    file_path = "sample/exceptions.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_6", repo_root, patch)

    assert result.status == "failed"
    assert any("Generic exception" in f["description"] or "broad" in f["description"].lower() for f in result.findings)


def test_rule6_accepts_specific_exception(repo_root: Path, run_rule) -> None:
    old = """
def fetch(data):
    try:
        return data["value"]
    except KeyError:
        raise KeyError("missing 'value' field")
"""
    new = """
def fetch(data):
    try:
        return data["value"]
    except KeyError:
        raise KeyError("missing 'value' field")
"""
    file_path = "sample/exceptions_ok.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_6", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
