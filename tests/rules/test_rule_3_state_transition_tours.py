from pathlib import Path

from tests.rules.conftest import make_patch, write_file


def test_rule3_flags_incorrect_transition(repo_root: Path, run_rule) -> None:
    old = """
TRANSITIONS = {
    ("OPENING", "connected"): "CONNECTED",
    ("CONNECTED", "close"): "CLOSED",
}

def advance_state(state, event):
    return TRANSITIONS[(state, event)]
"""
    new = """
TRANSITIONS = {
    ("OPENING", "connected"): "CONNECTED",
    ("CONNECTED", "close"): "CLOSED",
}

def advance_state(state, event):
    if (state, event) not in TRANSITIONS:
        raise KeyError(f"Unknown transition {state}/{event}")
    next_state = TRANSITIONS[(state, event)]
    if event == "close":
        # bug: forgets to move to CLOSED
        return state
    return next_state
"""
    file_path = "sample/state_machine.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_3", repo_root, patch)

    assert result.status == "failed"
    assert any("expected" in f["description"] for f in result.findings)


def test_rule3_accepts_valid_tours(repo_root: Path, run_rule) -> None:
    old = """
TRANSITIONS = {
    ("OPENING", "connected"): "CONNECTED",
    ("CONNECTED", "close"): "CLOSED",
}

def advance_state(state, event):
    return TRANSITIONS[(state, event)]
"""
    new = """
TRANSITIONS = {
    ("OPENING", "connected"): "CONNECTED",
    ("CONNECTED", "close"): "CLOSED",
}

def advance_state(state, event):
    return TRANSITIONS[(state, event)]
"""
    file_path = "sample/state_machine_ok.py"
    write_file(repo_root, file_path, new)
    patch = make_patch(old, new, file_path)

    result = run_rule("rule_3", repo_root, patch)

    assert result.status == "passed"
    assert result.findings == []
