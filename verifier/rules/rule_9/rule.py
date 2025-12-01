from __future__ import annotations

import threading
from typing import Optional, Tuple

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions
from verifier_harness.verifier.utils.diff_utils import parse_unified_diff


def _find_counter(func) -> Optional[Tuple[str, int]]:
    for name, value in func.__globals__.items():
        if "counter" in name.lower() and isinstance(value, int):
            return name, value
    return None


def _call_repeated(func, iterations: int, errors: list) -> None:
    for _ in range(iterations):
        try:
            func()
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)


def run_rule(repo_path: str, patch_str: str, workers: int = 4, iterations: int = 5, **kwargs) -> RuleResult:
    """Concurrency and interlock order checks (Rule 9)."""
    result = default_result("rule_9", "Concurrency and Interlock Order Checks")
    diff_info = parse_unified_diff(patch_str)
    changed_functions = gather_changed_functions(repo_path, patch_str)

    for func_info in changed_functions:
        counter_info = _find_counter(func_info.func)
        before_counter = counter_info[1] if counter_info else None
        errors: list = []
        threads = [
            threading.Thread(target=_call_repeated, args=(func_info.func, iterations, errors))
            for _ in range(workers)
        ]
        for thread in threads:
            thread.daemon = True
            thread.start()
        for thread in threads:
            thread.join(timeout=1.0)

        alive = [t for t in threads if t.is_alive()]
        if alive:
            result.add_finding(
                "Concurrent execution did not complete (possible deadlock)",
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["concurrency"],
            )
            continue
        if errors:
            result.add_finding(
                "Concurrent execution raised exceptions",
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["concurrency"],
            )
        if counter_info:
            after = func_info.func.__globals__.get(counter_info[0], before_counter)
            expected_growth = workers * iterations
            if after - before_counter < expected_growth:
                result.add_finding(
                    "Counter updates were lost during concurrent execution",
                    location=f"{func_info.path}:{func_info.lineno}",
                    taxonomy_tags=["concurrency"],
                )

    result.metrics["files_changed"] = len(diff_info)
    result.metrics["functions_checked"] = len(changed_functions)
    result.metrics["workers"] = workers
    result.metrics["iterations_per_worker"] = iterations
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
