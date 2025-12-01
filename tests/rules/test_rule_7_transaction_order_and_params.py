from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule7_detects_wrong_order(repo_root: Path, run_rule) -> None:
    old = """
EXPECTED_SEQUENCE = ["connect", "send", "close"]

def run_flow():
    return ["connect", "send", "close"]
"""
    new = """
EXPECTED_SEQUENCE = ["connect", "send", "close"]

def run_flow():
    # closes too early
    return ["connect", "close", "send"]
"""
    file_path = "sample/transaction.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_7", repo_root, patch)

    assert result.status == "failed"
    assert any("Expected order" in f["description"] for f in result.findings)


def test_rule7_accepts_correct_sequence(repo_root: Path, run_rule) -> None:
    old = """
EXPECTED_SEQUENCE = ["connect", "send", "close"]

def run_flow():
    return ["connect", "send", "close"]
"""
    new = """
EXPECTED_SEQUENCE = ["connect", "send", "close"]

def run_flow():
    return ["connect", "send", "close"]
"""
    file_path = "sample/transaction_ok.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_7", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
