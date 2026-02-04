from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from .planner import Plan


@dataclass
class GuardrailResult:
    ok: bool
    reason: Optional[str]
    context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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


def evaluate(plan: Plan) -> GuardrailResult:
    context: Dict[str, Any] = {}
    if not plan.primary_module:
        context["warning"] = "No module inferred from grounding; proceeding cautiously."
        return GuardrailResult(ok=True, reason=None, context=context)

    try:
        module = importlib.import_module(plan.primary_module)
    except Exception as exc:  # pragma: no cover - defensive
        context["warning"] = (
            f"Failed to import {plan.primary_module}: {exc!r}. Proceeding without module context."
        )
        return GuardrailResult(ok=True, reason="import_warning", context=context)

    context["module"] = plan.primary_module
    if not plan.target_symbols:
        context["info"] = "Plan has no explicit target symbols."
        return GuardrailResult(ok=True, reason=None, context=context)

    missing: List[str] = []
    signature_hints: Dict[str, Any] = {}
    required_args: Dict[str, List[str]] = {}
    resolved: Dict[str, str] = {}
    module_classes = {
        name: obj for name, obj in inspect.getmembers(module, inspect.isclass)
    }
    for symbol in plan.target_symbols:
        attr = getattr(module, symbol, None)
        if attr is None:
            owner_name = None
            owner = None
            for class_name, class_obj in module_classes.items():
                if hasattr(class_obj, symbol):
                    owner_name = class_name
                    owner = getattr(class_obj, symbol)
                    break
            if owner is None:
                missing.append(symbol)
                continue
            attr = owner
            resolved[symbol] = f"{plan.primary_module}.{owner_name}.{symbol}"
        else:
            resolved[symbol] = f"{plan.primary_module}.{symbol}"
        if inspect.isfunction(attr) or inspect.ismethod(attr):
            signature, required, autofill = _describe_signature(attr)
            signature_hints[symbol] = {
                "signature": signature,
                "autofill": autofill,
            }
            if required:
                required_args[symbol] = required

    if missing:
        context["warnings"] = context.get("warnings", [])
        context["warnings"].append(
            f"Symbols not found even after scanning classes: {', '.join(missing)}"
        )

    if resolved:
        context["resolved_symbols"] = resolved

    if signature_hints:
        context["signatures"] = signature_hints
    if required_args:
        context["required_args"] = required_args
    return GuardrailResult(ok=True, reason=None, context=context)
