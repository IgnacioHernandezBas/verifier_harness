from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule9_detects_deadlock(repo_root: Path, run_rule) -> None:
    old = """
import threading

LOCK = threading.Lock()
COUNTER = 0

def increment():
    global COUNTER
    with LOCK:
        COUNTER += 1
"""
    new = """
import threading

LOCK = threading.Lock()
COUNTER = 0

def increment():
    global COUNTER
    LOCK.acquire()
    COUNTER += 1
    # bug: never releases the lock
"""
    file_path = "sample/concurrency.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_9", repo_root, patch)

    assert result.status == "failed"
    assert any("deadlock" in f["description"].lower() for f in result.findings)


def test_rule9_accepts_clean_concurrency(repo_root: Path, run_rule) -> None:
    old = """
import threading

LOCK = threading.Lock()
COUNTER = 0

def increment():
    global COUNTER
    with LOCK:
        COUNTER += 1
"""
    new = """
import threading

LOCK = threading.Lock()
COUNTER = 0

def increment():
    global COUNTER
    with LOCK:
        COUNTER += 1
"""
    file_path = "sample/concurrency_ok.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_9", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
