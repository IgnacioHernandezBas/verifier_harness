
import ast
import inspect
import textwrap
from typing import List, Set

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions
from verifier_harness.verifier.utils.diff_utils import parse_unified_diff


def _names_in_context(node: ast.AST, ctx) -> List[str]:
    return [n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ctx)]


def _collect_assignments(stmt: ast.AST) -> Set[str]:
    assigned: Set[str] = set(_names_in_context(stmt, ast.Store))
    if isinstance(stmt, ast.Assign):
        if isinstance(stmt.value, ast.Call) and isinstance(stmt.targets[0], ast.Name):
            func_name = ""
            if isinstance(stmt.value.func, ast.Name):
                func_name = stmt.value.func.id
            elif isinstance(stmt.value.func, ast.Attribute):
                func_name = stmt.value.func.attr
            if any(keyword in func_name for keyword in ("open", "connect", "acquire")):
                assigned.add(stmt.targets[0].id)
    return assigned


def _scan_def_use(func) -> List[str]:
    try:
        source = inspect.getsource(func)
    except OSError:
        return []
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []

    func_node = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)), None)
    if func_node is None:
        return []

    assigned: Set[str] = {arg.arg for arg in func_node.args.args}
    findings: List[str] = []
    resource_candidates: Set[str] = set()

    for stmt in func_node.body:
        uses = _names_in_context(stmt, ast.Load)
        for name in uses:
            if name not in assigned:
                findings.append(f"Use of '{name}' before it is definitely defined")
        if isinstance(stmt, ast.If):
            assigned_if = set().union(*[_collect_assignments(s) for s in stmt.body])
            assigned_else = set().union(*[_collect_assignments(s) for s in stmt.orelse])
            conditional_only = (assigned_if ^ assigned_else) - assigned
            if conditional_only:
                for name in sorted(conditional_only):
                    findings.append(f"Use of '{name}' may occur without definition (conditional path)")
        assignments = _collect_assignments(stmt)
        assigned.update(assignments)
        resource_candidates.update(assignments)

    source_text = textwrap.dedent(source)
    for res in resource_candidates:
        if f"{res}.close" not in source_text and f"{res}.release" not in source_text:
            findings.append(f"Resource '{res}' is acquired but never closed or released")

    return findings


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """Definition–use execution (Rule 4)."""
    result = default_result("rule_4", "Definition–Use Execution")
    diff_info = parse_unified_diff(patch_str)
    changed_functions = gather_changed_functions(repo_path, patch_str)

    for func_info in changed_functions:
        def_use_findings = _scan_def_use(func_info.func)
        for desc in def_use_findings:
            result.add_finding(
                desc,
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["def-use"],
            )

    result.metrics["files_changed"] = len(diff_info)
    result.metrics["functions_checked"] = len(changed_functions)
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
