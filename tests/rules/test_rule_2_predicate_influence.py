from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule2_flags_masked_clause(repo_root: Path, run_rule) -> None:
    old = """
def allow_request(flag: bool, ready: bool) -> bool:
    return flag and ready
"""
    new = """
def allow_request(flag: bool, ready: bool) -> bool:
    # mistakenly duplicated clause masks 'ready'
    return flag and flag
"""
    file_path = "sample/predicate.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_2", repo_root, patch)

    assert result.status == "failed"
    assert any("masked" in f["description"] for f in result.findings)


def test_rule2_accepts_effective_predicate(repo_root: Path, run_rule) -> None:
    old = """
def ok(flag: bool, ready: bool) -> bool:
    return flag and ready
"""
    new = """
def ok(flag: bool, ready: bool) -> bool:
    return flag and ready
"""
    file_path = "sample/predicate_clean.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_2", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
