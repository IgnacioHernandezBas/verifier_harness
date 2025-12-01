from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule8_flags_silent_defaults(repo_root: Path, run_rule) -> None:
    old = """
EXPECTED_FIELDS = {"name": str, "count": int}

def parse(payload):
    name = payload["name"]
    count = int(payload["count"])
    return {"name": name, "count": count}
"""
    new = """
EXPECTED_FIELDS = {"name": str, "count": int}

def parse(payload):
    # silently defaults instead of failing
    return {"name": payload.get("name", ""), "count": payload.get("count", 0)}
"""
    file_path = "sample/structured.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_8", repo_root, patch)

    assert result.status == "failed"
    assert any("Missing field" in f["description"] for f in result.findings)


def test_rule8_accepts_strict_parser(repo_root: Path, run_rule) -> None:
    old = """
EXPECTED_FIELDS = {"name": str, "count": int}

def parse(payload):
    name = payload["name"]
    count = int(payload["count"])
    return {"name": name, "count": count}
"""
    new = """
EXPECTED_FIELDS = {"name": str, "count": int}

def parse(payload):
    name = payload["name"]
    count = int(payload["count"])
    return {"name": name, "count": count}
"""
    file_path = "sample/structured_ok.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_8", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
