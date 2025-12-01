from __future__ import annotations

from typing import Dict, List, Tuple

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions, load_module_from_repo
from verifier_harness.verifier.utils.diff_utils import filter_paths_to_py, parse_unified_diff


def _flatten_transitions(raw_transitions: Dict) -> Dict[Tuple[str, str], str]:
    flattened: Dict[Tuple[str, str], str] = {}
    for key, value in raw_transitions.items():
        if isinstance(key, tuple) and len(key) == 2:
            flattened[(key[0], key[1])] = value
        elif isinstance(value, dict):
            for event, dest in value.items():
                flattened[(str(key), str(event))] = dest
    return flattened


def _collect_transitions(module) -> Dict[Tuple[str, str], str]:
    for attr in ("TRANSITIONS", "STATE_GRAPH"):
        maybe = getattr(module, attr, None)
        if isinstance(maybe, dict):
            return _flatten_transitions(maybe)
    return {}


def _pick_driver(changed_functions) -> List:
    preferred_names = {"advance_state", "apply_event", "transition", "handle_event"}
    explicit = [fi for fi in changed_functions if fi.name in preferred_names]
    return explicit or list(changed_functions)


def _exercise_transition(driver, state: str, event: str):
    try:
        return driver(state, event)
    except Exception:
        return None


def _two_step_tour(driver, transitions: Dict[Tuple[str, str], str]) -> bool:
    items = list(transitions.items())
    if len(items) < 2:
        return True
    (start, event1), mid_state = items[0]
    next_hop = None
    for (state, event), dest in items[1:]:
        if state == mid_state:
            next_hop = (event, dest)
            break
    if next_hop is None:
        return True
    second_event, expected_dest = next_hop
    first_result = _exercise_transition(driver, start, event1)
    if first_result is None:
        return False
    second_result = _exercise_transition(driver, first_result, second_event)
    return second_result == expected_dest


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """State transition tours (Rule 3)."""
    result = default_result("rule_3", "State Transition Tours")
    diff_info = parse_unified_diff(patch_str)
    changed_files = filter_paths_to_py(list(diff_info.keys()))
    changed_functions = gather_changed_functions(repo_path, patch_str)

    transitions_checked = 0

    for rel_path in changed_files:
        module = load_module_from_repo(repo_path, rel_path)
        if module is None:
            continue
        transitions = _collect_transitions(module)
        if not transitions:
            continue

        drivers = _pick_driver([fi for fi in changed_functions if fi.path == rel_path])
        if not drivers:
            continue

        allowed_states = set(transitions.keys()) | set(transitions.values())
        for driver in drivers:
            for (state, event), expected_dest in transitions.items():
                observed = _exercise_transition(driver.func, state, event)
                transitions_checked += 1
                if observed != expected_dest:
                    result.add_finding(
                        f"Transition ({state}, {event}) expected '{expected_dest}' but observed '{observed}'",
                        location=f"{rel_path}:{driver.lineno}",
                        taxonomy_tags=["state-transition"],
                    )
            if not _two_step_tour(driver.func, transitions):
                result.add_finding(
                    "Two-step tour across modified transitions failed",
                    location=f"{rel_path}:{driver.lineno}",
                    taxonomy_tags=["state-transition"],
                )

    result.metrics["files_changed"] = len(changed_files)
    result.metrics["functions_checked"] = len(changed_functions)
    result.metrics["transitions_checked"] = transitions_checked
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
