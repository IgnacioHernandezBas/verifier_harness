from __future__ import annotations

import inspect
from typing import List, Sequence

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions, load_module_from_repo
from verifier_harness.verifier.utils.diff_utils import filter_paths_to_py, parse_unified_diff


def _expected_sequence(module) -> List[str]:
    for attr in ("EXPECTED_SEQUENCE", "EXPECTED_ORDER"):
        value = getattr(module, attr, None)
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
    return []


def _check_sequence(observed: Sequence[str], expected: Sequence[str]) -> List[str]:
    findings: List[str] = []
    if list(observed) != list(expected):
        findings.append(f"Expected order {list(expected)}, observed {list(observed)}")
    missing = [step for step in expected if step not in observed]
    if missing:
        findings.append(f"Missing steps: {missing}")
    return findings


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """Transaction order and parameter contracts (Rule 7)."""
    result = default_result("rule_7", "Transaction Order and Parameter Contracts")
    diff_info = parse_unified_diff(patch_str)
    changed_files = filter_paths_to_py(list(diff_info.keys()))
    changed_functions = gather_changed_functions(repo_path, patch_str)

    for rel_path in changed_files:
        module = load_module_from_repo(repo_path, rel_path)
        if module is None:
            continue
        expected = _expected_sequence(module)
        for func_info in [fi for fi in changed_functions if fi.path == rel_path]:
            sig = inspect.signature(func_info.func)
            required_params = [
                p for p in sig.parameters.values()
                if p.default is inspect._empty and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            if required_params:
                continue  # unable to safely synthesize inputs
            try:
                observed = func_info.func()
            except Exception:
                result.add_finding(
                    f"{func_info.name} failed during transaction simulation",
                    location=f"{rel_path}:{func_info.lineno}",
                    taxonomy_tags=["transaction-order"],
                )
                continue
            if expected and isinstance(observed, (list, tuple)):
                issues = _check_sequence(observed, expected)
                for desc in issues:
                    result.add_finding(
                        desc,
                        location=f"{rel_path}:{func_info.lineno}",
                        taxonomy_tags=["transaction-order"],
                    )

    result.metrics["files_changed"] = len(changed_files)
    result.metrics["functions_checked"] = len(changed_functions)
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
