from __future__ import annotations

import inspect
from typing import Dict

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions
from verifier_harness.verifier.utils.diff_utils import parse_unified_diff


def _resource_containers(func) -> Dict[str, object]:
    containers: Dict[str, object] = {}
    for name, obj in func.__globals__.items():
        lower = name.lower()
        if any(keyword in lower for keyword in ("resource", "handle", "connection", "open")) and isinstance(obj, (list, set, dict)):
            containers[name] = obj
    return containers


def _snapshot(containers: Dict[str, object]) -> Dict[str, int]:
    snapshot: Dict[str, int] = {}
    for name, obj in containers.items():
        try:
            snapshot[name] = len(obj)
        except Exception:
            snapshot[name] = 0
    return snapshot


def run_rule(repo_path: str, patch_str: str, iterations: int = 30, **kwargs) -> RuleResult:
    """Resource lifecycle under load (Rule 5)."""
    result = default_result("rule_5", "Resource Lifecycle Under Load")
    diff_info = parse_unified_diff(patch_str)
    changed_functions = gather_changed_functions(repo_path, patch_str)

    for func_info in changed_functions:
        sig = inspect.signature(func_info.func)
        params = [
            p for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD) and p.default is inspect._empty
        ]
        if params:
            continue  # skip functions that require inputs we cannot synthesize

        containers = _resource_containers(func_info.func)
        before = _snapshot(containers)
        for _ in range(iterations):
            try:
                func_info.func()
            except Exception:
                result.add_finding(
                    f"{func_info.name} raised during load iteration",
                    location=f"{func_info.path}:{func_info.lineno}",
                    taxonomy_tags=["resource-lifecycle"],
                )
                break
        after = _snapshot(containers)

        for name, start_count in before.items():
            growth = after.get(name, start_count) - start_count
            if growth > 0:
                result.add_finding(
                    f"Resource container '{name}' grew by {growth} without being reclaimed",
                    location=f"{func_info.path}:{func_info.lineno}",
                    taxonomy_tags=["resource-lifecycle"],
                )

    result.metrics["files_changed"] = len(diff_info)
    result.metrics["functions_checked"] = len(changed_functions)
    result.metrics["iterations"] = iterations
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
