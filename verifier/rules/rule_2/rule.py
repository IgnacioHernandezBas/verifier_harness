
import ast
import inspect
import textwrap
from typing import List, Set

from verifier_harness.verifier.rules.base import RuleResult, default_result
from verifier_harness.verifier.rules.helpers import gather_changed_functions, parse_patch_by_file


def _find_masked_clauses(func) -> List[str]:
    try:
        source = inspect.getsource(func)
    except OSError:
        return []
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []

    masked: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            names = []
            for value in node.values:
                if isinstance(value, ast.Name):
                    names.append(value.id)
                elif isinstance(value, ast.Constant) and isinstance(value.value, bool):
                    const = "True" if value.value else "False"
                    masked.append(f"Boolean expression contains constant {const}")
            duplicates = {name for name in names if names.count(name) > 1}
            for dup in duplicates:
                masked.append(f"Condition '{dup}' appears multiple times and may be masked")
    return masked


def _mc_dc_probe(func) -> Set[str]:
    sig = inspect.signature(func)
    params = [
        p for p in sig.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(params) == 0 or len(params) > 3:
        return set()

    enabling_inputs = [True] * len(params)
    try:
        baseline = func(*enabling_inputs)
    except Exception:
        return set()

    masked: Set[str] = set()
    for idx, param in enumerate(params):
        toggled = list(enabling_inputs)
        toggled[idx] = False
        try:
            outcome = func(*toggled)
        except Exception:
            masked.add(param.name)
            continue
        if outcome == baseline:
            masked.add(param.name)
    return masked


def run_rule(repo_path: str, patch_str: str, **kwargs) -> RuleResult:
    """Predicate influence / MC/DC style probing (Rule 2)."""
    result = default_result("rule_2", "Predicate Influence")
    changed_functions = gather_changed_functions(repo_path, patch_str)
    patch_data = parse_patch_by_file(patch_str)

    for func_info in changed_functions:
        masked_static = _find_masked_clauses(func_info.func)
        for desc in masked_static:
            result.add_finding(
                desc,
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["predicate", "312x"],
            )

        masked_params = _mc_dc_probe(func_info.func)
        for name in masked_params:
            result.add_finding(
                f"Input '{name}' does not independently influence the predicate outcome",
                location=f"{func_info.path}:{func_info.lineno}",
                taxonomy_tags=["predicate", "244x"],
            )

    result.metrics["functions_checked"] = len(changed_functions)
    result.metrics["files_changed"] = len(patch_data)
    if result.status not in ("failed", "skipped"):
        result.status = "passed"
    return result
