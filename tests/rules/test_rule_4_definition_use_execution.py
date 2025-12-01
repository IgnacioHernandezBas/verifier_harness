from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule4_detects_use_before_def(repo_root: Path, run_rule) -> None:
    old = """
def fetch(flag: bool):
    if flag:
        data = "ok"
    else:
        data = "fallback"
    return data
"""
    new = """
def fetch(flag: bool):
    if flag:
        data = "ok"
    # missing else branch leaves 'data' undefined
    return data
"""
    file_path = "sample/def_use.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_4", repo_root, patch)

    assert result.status == "failed"
    assert any("Use of 'data'" in f["description"] for f in result.findings)


def test_rule4_detects_missing_cleanup(repo_root: Path, run_rule) -> None:
    old = """
def load(path: str):
    handle = open(path)
    data = handle.read()
    handle.close()
    return data
"""
    new = """
def load(path: str):
    handle = open(path)
    data = handle.read()
    # missing cleanup
    return data
"""
    file_path = "sample/resource_cleanup.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_4", repo_root, patch)

    assert result.status == "failed"
    assert any("never closed" in f["description"] for f in result.findings)


def test_rule4_accepts_clean_def_use(repo_root: Path, run_rule) -> None:
    old = """
def compute(x):
    return x * 2
"""
    new = """
def compute(x):
    return x * 2
"""
    file_path = "sample/def_use_clean.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_4", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
