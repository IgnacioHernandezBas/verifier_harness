from __future__ import annotations

import ast
import inspect
import textwrap
from typing import List

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions
from verifier_harness.verifier.utils.diff_utils import parse_unified_diff


def _exception_issues(func) -> List[str]:
    try:
        source = inspect.getsource(func)
    except OSError:
        return []
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []

    issues: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append("Bare except handler obscures specific errors")
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                issues.append("Catches broad Exception instead of specific types")
        elif isinstance(node, ast.Raise):
            exc = node.exc
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                if exc.func.id in ("Exception", "RuntimeError"):
                    issues.append(f"Generic exception type '{exc.func.id}' used")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("error", "exception"):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    msg = node.args[0].value
                    if all(keyword not in msg for keyword in ("id", "code", "reason")):
                        issues.append("Error message missing identifiers or context")
    return issues


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """Robust exception and message paths (Rule 6)."""
    result = default_result("rule_6", "Robust Exception Paths")
    diff_info = parse_unified_diff(patch_str)
    changed_functions = gather_changed_functions(repo_path, patch_str)

    for func_info in changed_functions:
        issues = _exception_issues(func_info.func)
        for desc in issues:
            result.add_finding(
                desc,
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["exception-paths"],
            )

    result.metrics["files_changed"] = len(diff_info)
    result.metrics["functions_checked"] = len(changed_functions)
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
