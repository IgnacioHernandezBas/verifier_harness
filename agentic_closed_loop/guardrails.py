from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

from .planner import Plan


def _extract_imports_from_test_patches(plan: Plan) -> Dict[str, List[str]]:
    """
    Extract import statements from test patch files to show what imports are known to work.

    Returns dict with:
    - 'import_lines': List of raw import statements
    - 'imported_names': List of specific names imported
    """
    test_patch_files = plan.context.commit_diff.test_patch_files
    repo_path = plan.context.repo_path

    if not test_patch_files or not repo_path:
        return {"import_lines": [], "imported_names": []}

    import_lines: Set[str] = set()
    imported_names: Set[str] = set()

    for test_file in test_patch_files:
        file_path = Path(repo_path) / test_file
        if not file_path.exists():
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            # Extract import lines using regex (simpler than AST for this)
            import_pattern = r'^(?:from\s+[\w.]+\s+import\s+.+|import\s+[\w.,\s]+)'
            for line in content.split('\n'):
                line = line.strip()
                if re.match(import_pattern, line):
                    import_lines.add(line)

                    # Extract specific names
                    if 'from' in line and 'import' in line:
                        # from X import Y, Z
                        parts = line.split('import', 1)
                        if len(parts) == 2:
                            names = parts[1].split(',')
                            for name in names:
                                name = name.strip().split(' as ')[0].strip()
                                if name and not name.startswith('('):
                                    imported_names.add(name)
                    elif 'import' in line and 'from' not in line:
                        # import X, Y
                        parts = line.replace('import', '').split(',')
                        for name in parts:
                            name = name.strip().split(' as ')[0].strip()
                            if name:
                                imported_names.add(name)
        except Exception:
            continue  # Skip files that can't be read

    return {
        "import_lines": sorted(list(import_lines)),
        "imported_names": sorted(list(imported_names))
    }


def _introspect_module(plan: Plan, module: Any) -> Dict[str, List[str]]:
    """
    Introspect a module to discover available classes, functions, and other members.

    Returns dict with:
    - 'classes': List of available class names
    - 'functions': List of available function names
    - 'all_members': List of all public members
    """
    try:
        all_members = [name for name in dir(module) if not name.startswith('_')]
        classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]
        functions = [name for name, obj in inspect.getmembers(module, inspect.isfunction)]

        return {
            "classes": sorted(classes),
            "functions": sorted(functions),
            "all_members": sorted(all_members)
        }
    except Exception:
        return {"classes": [], "functions": [], "all_members": []}


@dataclass
class GuardrailCheckResult:
    label: str
    passed: bool
    action: Optional[str]
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GuardrailResult:
    ok: bool
    reason: Optional[str]
    context: Dict[str, Any]
    checks: List[GuardrailCheckResult]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [check.to_dict() for check in self.checks]
        return payload


def evaluate(plan: Plan) -> GuardrailResult:
    context: Dict[str, Any] = {}
    checks: List[GuardrailCheckResult] = []

    if not plan.primary_module:
        context["warning"] = "No module inferred from grounding; proceeding cautiously."
        return GuardrailResult(
            ok=True,
            reason=None,
            context=context,
            checks=[
                GuardrailCheckResult(
                    label="import_check",
                    passed=False,
                    action="Infer module from grounding or set target module manually.",
                    details={"message": "Missing primary module."},
                )
            ],
        )

    import_check, module_obj = _run_import_check(plan)
    checks.append(import_check)

    # If import fails, continue with degraded functionality (no signatures)
    # The actual test will be validated in the container with correct Python version
    if not import_check.passed or not module_obj:
        context["module"] = plan.primary_module
        context["import_warning"] = "Module import failed in host environment; proceeding without signature hints."
        if plan.context.repo_path:
            context["repo_path"] = plan.context.repo_path

        # Skip signature/probe checks since we don't have module object
        fixture_check = _run_fixture_check(plan)
        checks.append(fixture_check)

        # Allow continuation despite import failure
        ok = True  # Non-blocking: let test generation proceed
        return GuardrailResult(ok=ok, reason=None, context=context, checks=checks)

    context["module"] = plan.primary_module
    if plan.context.repo_path:
        context["repo_path"] = plan.context.repo_path

    signature_check, callables, signature_context = _run_signature_check(plan, module_obj)
    checks.append(signature_check)
    context.update(signature_context)

    fixture_check = _run_fixture_check(plan)
    checks.append(fixture_check)

    probe_check = _run_probe_check(plan, callables)
    checks.append(probe_check)

    ok = all(check.passed for check in checks if check.label != "fixture_check")
    reason = next((check.label for check in checks if not check.passed), None)
    return GuardrailResult(ok=ok, reason=reason, context=context, checks=checks)


def _run_import_check(plan: Plan) -> Tuple[GuardrailCheckResult, Optional[Any]]:
    inserted = False
    repo_path = plan.context.repo_path
    if repo_path and repo_path not in sys.path:
        sys.path.insert(0, repo_path)
        inserted = True
    try:
        module = importlib.import_module(plan.primary_module)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - defensive
        if inserted and repo_path:
            try:
                sys.path.remove(repo_path)
            except ValueError:
                pass
        return GuardrailCheckResult(
            label="import_check",
            passed=False,
            action="Verify module path or update PYTHONPATH before running tests.",
            details={"error": repr(exc), "repo_path": repo_path},
        ), None
    finally:
        if inserted and repo_path:
            try:
                sys.path.remove(repo_path)
            except ValueError:
                pass

    return GuardrailCheckResult(
        label="import_check",
        passed=True,
        action=None,
        details={"module": plan.primary_module},
    ), module


def _run_signature_check(
    plan: Plan, module: Any
) -> Tuple[GuardrailCheckResult, Dict[str, Any], Dict[str, Any]]:
    if not plan.target_symbols:
        result = GuardrailCheckResult(
            label="signature_check",
            passed=True,
            action=None,
            details={"message": "No explicit target symbols."},
        )
        return result, {}, {}

    missing: List[str] = []
    signature_hints: Dict[str, Any] = {}
    required_args: Dict[str, List[str]] = {}
    resolved: Dict[str, str] = {}
    callables: Dict[str, Any] = {}

    module_classes = {
        name: obj for name, obj in inspect.getmembers(module, inspect.isclass)
    }

    for symbol in plan.target_symbols:
        attr = getattr(module, symbol, None)
        owner_name = None
        if attr is None:
            for class_name, class_obj in module_classes.items():
                if hasattr(class_obj, symbol):
                    owner_name = class_name
                    attr = getattr(class_obj, symbol)
                    break
        if attr is None:
            missing.append(symbol)
            continue
        if owner_name:
            resolved[symbol] = f"{plan.primary_module}.{owner_name}.{symbol}"
        else:
            resolved[symbol] = f"{plan.primary_module}.{symbol}"

        if inspect.isfunction(attr) or inspect.ismethod(attr):
            signature, required, autofill = _describe_signature(attr)
            hint = {
                "signature": signature,
                "autofill": autofill,
            }

            # Add instance method hints
            if owner_name:
                hint["is_instance_method"] = True
                hint["class_name"] = owner_name
                hint["usage_hint"] = (
                    f"This is an instance method of {owner_name}. "
                    f"You must create an instance first: "
                    f"obj = {owner_name}(...), then call obj.{symbol}(...)"
                )
            elif required and 'self' in required:
                hint["is_instance_method"] = True
                hint["usage_hint"] = (
                    f"This method requires 'self'. "
                    f"You must call it on an instance, not directly."
                )

            signature_hints[symbol] = hint
            if required:
                required_args[symbol] = required
            callables[symbol] = attr

    details: Dict[str, Any] = {}
    if missing:
        details["missing_symbols"] = missing
    if resolved:
        details["resolved_symbols"] = resolved
    if signature_hints:
        details["signatures"] = signature_hints
    if required_args:
        details["required_args"] = required_args

    passed = bool(resolved)
    action = None if passed else "Confirm symbol names or update grounding evidence."
    result = GuardrailCheckResult(
        label="signature_check",
        passed=passed,
        action=action,
        details=details,
    )
    return result, callables, details


def _run_fixture_check(plan: Plan) -> GuardrailCheckResult:
    fixtures = plan.context.fixtures
    details = {
        "available_fixtures": [fixture.name for fixture in fixtures],
        "count": len(fixtures),
    }
    action = None
    if fixtures and not plan.fixture_notes:
        action = "Plan lacks fixtures despite availability; consider leveraging them."
    return GuardrailCheckResult(
        label="fixture_check",
        passed=True,
        action=action,
        details=details,
    )


def _run_probe_check(plan: Plan, callables: Dict[str, Any]) -> GuardrailCheckResult:
    failures: List[str] = []
    skipped: List[str] = []
    successes: List[str] = []

    for symbol, func in callables.items():
        probe_ok, message = _execute_probe(symbol, func)
        if not probe_ok:
            failures.append(f"{symbol}: {message}")
        elif "skipped" in message.lower():
            skipped.append(f"{symbol}: {message}")
        else:
            successes.append(f"{symbol}: {message}")

    passed = not failures
    action = None
    if failures:
        action = (
            "Probe validation failed. These functions cannot be called without arguments. "
            "Ensure your test creates necessary instances/objects before calling these methods."
        )

    details = {
        "failures": failures,
        "skipped": skipped,
        "successes": successes,
        "probed_symbols": list(callables.keys()),
    }
    return GuardrailCheckResult(
        label="probe_check",
        passed=passed,
        action=action,
        details=details,
    )


def _execute_probe(symbol: str, func: Any) -> Tuple[bool, str]:
    """
    Probe a callable to ensure it can be invoked with default/no arguments.

    Returns (True, message) if probe should be skipped or succeeded.
    Returns (False, error) if probe failed.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return True, "Signature unavailable; skipping probe."

    params = list(sig.parameters.values())

    # Check 1: Skip instance/class methods (first param is self/cls)
    if params and params[0].name in ('self', 'cls'):
        return True, f"Instance/class method (first param: {params[0].name}); probe skipped."

    # Check 2: Skip if any required positional parameters exist
    required_params = [
        p for p in params
        if p.default is inspect.Parameter.empty
        and p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]

    if required_params:
        param_names = ', '.join(p.name for p in required_params)
        return True, f"Requires non-trivial inputs ({param_names}); probe skipped."

    # Check 3: Safe to probe - no required params
    try:
        func()
    except Exception as exc:
        return False, f"Raised {exc.__class__.__name__}: {exc}"

    return True, "Probe succeeded."


def _describe_signature(obj: Any) -> Tuple[str, List[str], Dict[str, Any]]:
    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        return "unknown()", [], {}

    params = []
    required: List[str] = []
    autofill: Dict[str, Any] = {}
    for name, param in sig.parameters.items():
        params.append(str(param))
        if (
            param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
            and param.default is inspect._empty
        ):
            required.append(name)
        elif param.default is not inspect._empty:
            autofill[name] = param.default
    return f"{obj.__name__}{sig}", required, autofill
