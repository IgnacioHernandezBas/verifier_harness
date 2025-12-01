from __future__ import annotations

import inspect
from typing import Any, Dict

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions, load_module_from_repo
from verifier_harness.verifier.utils.diff_utils import filter_paths_to_py, parse_unified_diff


def _build_valid_payload(schema: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, expected in schema.items():
        if expected is int:
            payload[key] = 1
        elif expected is float:
            payload[key] = 1.0
        elif expected is list:
            payload[key] = []
        elif expected is dict:
            payload[key] = {}
        else:
            payload[key] = "value"
    return payload


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """Structured input validation (Rule 8)."""
    result = default_result("rule_8", "Structured Input and Conversion Validation")
    diff_info = parse_unified_diff(patch_str)
    changed_files = filter_paths_to_py(list(diff_info.keys()))
    changed_functions = gather_changed_functions(repo_path, patch_str)

    for rel_path in changed_files:
        module = load_module_from_repo(repo_path, rel_path)
        if module is None:
            continue
        schema = getattr(module, "EXPECTED_FIELDS", None)
        if not isinstance(schema, dict):
            continue
        valid_payload = _build_valid_payload(schema)
        for func_info in [fi for fi in changed_functions if fi.path == rel_path]:
            sig = inspect.signature(func_info.func)
            params = [
                p for p in sig.parameters.values()
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            if len(params) != 1:
                continue
            try:
                func_info.func(valid_payload)
            except Exception as exc:
                result.add_finding(
                    f"Valid payload rejected: {exc}",
                    location=f"{rel_path}:{func_info.lineno}",
                    taxonomy_tags=["input-validation"],
                )
                continue

            # Missing field scenario
            missing_payload = dict(valid_payload)
            missing_key = next(iter(schema.keys()))
            missing_payload.pop(missing_key, None)
            try:
                func_info.func(missing_payload)
                result.add_finding(
                    f"Missing field '{missing_key}' did not raise an error",
                    location=f"{rel_path}:{func_info.lineno}",
                    taxonomy_tags=["input-validation"],
                )
            except Exception:
                pass

            # Wrong type scenario
            wrong_type_payload = dict(valid_payload)
            wrong_type_payload[next(iter(schema.keys()))] = object()
            try:
                func_info.func(wrong_type_payload)
                result.add_finding(
                    "Wrongly typed payload did not raise an error",
                    location=f"{rel_path}:{func_info.lineno}",
                    taxonomy_tags=["input-validation"],
                )
            except Exception:
                pass

    result.metrics["files_changed"] = len(changed_files)
    result.metrics["functions_checked"] = len(changed_functions)
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
