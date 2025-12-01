from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule5_flags_leak_under_load(repo_root: Path, run_rule) -> None:
    old = """
OPEN_HANDLES = []

def allocate():
    handle = object()
    OPEN_HANDLES.append(handle)
    OPEN_HANDLES.pop()
"""
    new = """
OPEN_HANDLES = []

def allocate():
    handle = object()
    # bug: never releases handle
    OPEN_HANDLES.append(handle)
"""
    file_path = "sample/resource_rule5.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_5", repo_root, patch)

    assert result.status == "failed"
    assert any("grew" in f["description"] for f in result.findings)


def test_rule5_accepts_balanced_lifecycle(repo_root: Path, run_rule) -> None:
    old = """
OPEN_HANDLES = []

def allocate():
    handle = object()
    OPEN_HANDLES.append(handle)
    OPEN_HANDLES.pop()
"""
    new = """
OPEN_HANDLES = []

def allocate():
    handle = object()
    OPEN_HANDLES.append(handle)
    OPEN_HANDLES.pop()
"""
    file_path = "sample/resource_ok.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_5", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
