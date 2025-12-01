from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule1_detects_off_by_one(repo_root: Path, run_rule) -> None:
    old = """
def should_retry(count: int) -> bool:
    return count >= 3
"""
    new = """
def should_retry(count: int) -> bool:
    # incorrect boundary change: now strictly greater
    return count > 3
"""
    file_path = "sample/boundaries.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_1", repo_root, patch)

    assert result.status == "failed"
    assert any("Boundary changed" in f["description"] for f in result.findings)
    assert result.metrics["boundary_probes"] >= 2


def test_rule1_passes_when_boundaries_hold(repo_root: Path, run_rule) -> None:
    old = """
def accepts(value: int) -> bool:
    return value > 10
"""
    new = """
def accepts(value: int) -> bool:
    return value >= 10
"""
    file_path = "sample/ok_boundaries.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_1", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []


def test_rule1_runner_cli_outputs_json(repo_root: Path, run_cli) -> None:
    old = """
def guard(num: int) -> bool:
    return num > 0
"""
    new = """
def guard(num: int) -> bool:
    return num > 0
"""
    file_path = "sample/cli_case.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    completed = run_cli("rule_1", repo_root, patch)

    assert completed.returncode == 0
    assert "rule_1" in completed.stdout
