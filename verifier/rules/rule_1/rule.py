
import ast
import inspect
import re
import textwrap
from typing import Dict, List, Tuple

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions, parse_patch_by_file
from verifier_harness.verifier.utils.diff_utils import parse_unified_diff


INCLUSIVE_TO_EXCLUSIVE = [(">=", ">"), ("<=", "<")]


def _normalize_op(line: str, old_op: str, new_op: str) -> Tuple[str, str]:
    return line.replace(old_op, "__OP__"), line.replace(new_op, "__OP__")


def _detect_operator_shifts(patch_data: Dict[str, Dict[str, List[str]]]) -> List[Tuple[str, str]]:
    """Return (path, description) for swapped boundary operators."""
    findings: List[Tuple[str, str]] = []
    pattern_tpl = r"([A-Za-z_][\w]*)\s*({op})\s*(-?\d+(?:\.\d+)?)"
    for path, change in patch_data.items():
        added = change.get("added", [])
        removed = change.get("removed", [])
        for old_op, new_op in INCLUSIVE_TO_EXCLUSIVE:
            old_pattern = re.compile(pattern_tpl.format(op=re.escape(old_op)))
            new_pattern = re.compile(pattern_tpl.format(op=re.escape(new_op)))
            for removed_line in removed:
                match_old = old_pattern.search(removed_line)
                if not match_old:
                    continue
                var_old, _, value_old = match_old.groups()
                for added_line in added:
                    match_new = new_pattern.search(added_line)
                    if not match_new:
                        continue
                    var_new, _, value_new = match_new.groups()
                    if var_old == var_new and value_old == value_new:
                        findings.append(
                            (
                                path,
                                f"Boundary changed from {old_op} to {new_op}: '{removed_line.strip()}' -> '{added_line.strip()}'",
                            )
                        )
    return findings


def _detect_constant_shift(patch_data: Dict[str, Dict[str, List[str]]]) -> List[Tuple[str, str]]:
    """Detect small constant changes that likely move boundaries."""
    findings: List[Tuple[str, str]] = []
    pattern = re.compile(r"([A-Za-z_][\w]*)\s*([<>]=?)\s*(-?\d+(?:\.\d+)?)")
    for path, change in patch_data.items():
        added = change.get("added", [])
        removed = change.get("removed", [])
        for removed_line in removed:
            match_removed = pattern.search(removed_line)
            if not match_removed:
                continue
            var_removed, op_removed, value_removed = match_removed.groups()
            for added_line in added:
                match_added = pattern.search(added_line)
                if not match_added:
                    continue
                var_added, op_added, value_added = match_added.groups()
                if var_removed != var_added or op_removed != op_added:
                    continue
                try:
                    delta = float(value_added) - float(value_removed)
                except ValueError:
                    continue
                if abs(delta) == 1.0:
                    findings.append((path, f"Boundary constant for '{var_added}' moved from {value_removed} to {value_added}"))
    return findings


def _extract_thresholds(func) -> List[float]:
    try:
        source = inspect.getsource(func)
    except OSError:
        return []
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []
    values: List[float] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                    values.append(float(comparator.value))
    return values


def _probe_boundaries(func_info, thresholds: List[float]) -> Tuple[int, bool]:
    """Execute boundary probes for simple functions. Returns (runs, collapse_flag)."""
    func = func_info.func
    sig = inspect.signature(func)
    params = [
        p for p in sig.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(params) == 0 or len(params) > 2:
        return 0, False
    if not thresholds:
        thresholds = [0.0]

    runs = 0
    collapsed = False
    for threshold in thresholds[:1]:  # only the first threshold keeps runtime bounded
        boundary_points = [threshold - 1, threshold, threshold + 1]
        outcomes = []
        for point in boundary_points:
            args = [point] * len(params)
            try:
                outcome = func(*args)
            except Exception:
                continue
            runs += 1
            outcomes.append(outcome)
        if outcomes and len(set(outcomes)) == 1:
            collapsed = True
    return runs, collapsed


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """Boundary and intersection probing (Rule 1)."""
    result = default_result("rule_1", "Boundary and Intersection Probing")
    patch_data = parse_patch_by_file(patch_str)

    operator_findings = _detect_operator_shifts(patch_data)
    constant_findings = _detect_constant_shift(patch_data)
    for path, desc in operator_findings + constant_findings:
        result.add_finding(desc, location=path, taxonomy_tags=["boundary"])

    diff_info = parse_unified_diff(patch_str)
    changed_functions = gather_changed_functions(repo_path, patch_str)
    probes_run = 0
    for func_info in changed_functions:
        thresholds = _extract_thresholds(func_info.func)
        runs, collapsed = _probe_boundaries(func_info, thresholds)
        probes_run += runs
        if collapsed:
            result.add_finding(
                f"Boundary inputs for '{func_info.name}' collapse to the same outcome",
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["boundary", "intersection"],
            )

    result.metrics["files_changed"] = len(diff_info)
    result.metrics["functions_checked"] = len(changed_functions)
    result.metrics["boundary_probes"] = probes_run
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
