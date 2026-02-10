from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from claim_test_generation.claim_test_generator import (
    VLLMClient,
    generate_pytest_for_claim,
)

from .planner import Plan, plan_to_messages
from .test_sketcher import TestSketch


def generate_pytest_from_sketch(
    *,
    claim: Dict[str, Any],
    sample: Dict[str, Any],
    plan: Plan,
    sketch: TestSketch,
    guardrail_context: Dict[str, Any],
    guardrail_checks: List[Dict[str, Any]],
    client: VLLMClient,
    previous_feedback: Optional[str],
) -> Tuple[str, Dict[str, Any]]:
    extra_messages = _build_extra_messages(
        plan=plan,
        sketch=sketch,
        guardrail_context=guardrail_context,
        guardrail_checks=guardrail_checks,
        previous_feedback=previous_feedback,
    )
    code = generate_pytest_for_claim(
        claim,
        repo=sample.get("repo", "unknown_repo"),
        instance_id=plan.instance_id,
        client=client,
        extra_messages=extra_messages,
    )
    code, coverage = _enforce_checklist(code, sketch.checklist)
    return code, coverage


def _build_extra_messages(
    *,
    plan: Plan,
    sketch: TestSketch,
    guardrail_context: Dict[str, Any],
    guardrail_checks: List[Dict[str, Any]],
    previous_feedback: Optional[str],
) -> List[Dict[str, str]]:
    messages = plan_to_messages(
        plan, guardrail_context=guardrail_context, previous_feedback=previous_feedback
    )
    guardrail_block = json.dumps(
        {"context": guardrail_context, "checks": guardrail_checks},
        ensure_ascii=False,
        indent=2,
    )
    sketch_block = sketch.to_prompt_block()

    # Build detailed instructions based on guardrail context
    signature_guidance = _build_signature_guidance(guardrail_context)
    feedback_guidance = _build_feedback_guidance(previous_feedback, guardrail_context)

    instructions = (
        "Follow this test sketch exactly. Every checklist line must appear as a comment "
        "and the implemented test must demonstrate each assertion described.\n\n"
        f"Test sketch:\n{sketch_block}\n\n"
        "Guardrail diagnostics:\n"
        f"{guardrail_block}\n\n"
        f"{signature_guidance}\n"
        f"{feedback_guidance}\n"
    )
    messages.append({"role": "user", "content": instructions})
    return messages


def _build_signature_guidance(guardrail_context: Dict[str, Any]) -> str:
    """Build guidance for handling function signatures and instance methods."""
    signatures = guardrail_context.get("signatures", {})

    # Check if signature hints are unavailable due to import failure
    import_warning = guardrail_context.get("import_warning")
    if not signatures and import_warning:
        return (
            "## ⚠️ NOTE: Signature Hints Unavailable\n"
            "Module import failed in host environment.\n"
            "**Use the grounding source_excerpt** in your plan context to find the actual function definition.\n"
            "Pay attention to:\n"
            "- The FIRST parameter (especially if it's 'self' or requires creating an object)\n"
            "- All required parameters and their order\n\n"
        )

    if not signatures:
        return ""

    guidance_parts = ["## IMPORTANT: Function Signature Guidance\n"]

    for symbol, sig_info in signatures.items():
        sig_str = sig_info.get("signature", "")
        is_instance = sig_info.get("is_instance_method", False)
        usage_hint = sig_info.get("usage_hint", "")

        if is_instance:
            class_name = sig_info.get("class_name", "UnknownClass")
            guidance_parts.append(
                f"**{symbol}**: This is an INSTANCE METHOD of {class_name}.\n"
                f"  - Signature: `{sig_str}`\n"
                f"  - ⚠️ You CANNOT call {symbol}() directly!\n"
                f"  - ✓ You MUST create a {class_name} instance first:\n"
                f"      ```python\n"
                f"      obj = {class_name}(...)  # Create instance\n"
                f"      result = obj.{symbol}(...)  # Call method on instance\n"
                f"      ```\n"
            )
        elif "self" in sig_str or "cls" in sig_str:
            guidance_parts.append(
                f"**{symbol}**: Requires self/cls parameter.\n"
                f"  - Signature: `{sig_str}`\n"
                f"  - You must call this on an object instance, not directly.\n"
            )
        else:
            # Regular function with required params
            required = guardrail_context.get("required_args", {}).get(symbol, [])
            if required:
                guidance_parts.append(
                    f"**{symbol}**: Requires parameters: {', '.join(required)}\n"
                    f"  - Signature: `{sig_str}`\n"
                )

    return "\n".join(guidance_parts) if len(guidance_parts) > 1 else ""


def _build_feedback_guidance(
    previous_feedback: Optional[str], guardrail_context: Dict[str, Any]
) -> str:
    """Build guidance based on previous failure feedback."""
    if not previous_feedback:
        return ""

    guidance = ["## CRITICAL: Learn from Previous Failure\n"]
    guidance.append(f"Previous attempt failed with:\n```\n{previous_feedback}\n```\n")

    # Detect specific error patterns and provide targeted advice
    if "missing 1 required positional argument" in previous_feedback:
        # Check if signature hints were available
        has_signatures = bool(guardrail_context.get("signatures"))

        # Extract the missing argument
        if "argument: " in previous_feedback:
            arg_part = previous_feedback.split("argument: ")[1].split("\n")[0].strip("'\"")
            guidance.append(
                f"\n**ERROR ANALYSIS**: The function is missing its FIRST parameter.\n"
                f"This usually means:\n"
                f"1. If the error mentions 'self', you need to create an instance of the parent class\n"
                f"2. Otherwise, you need to create/provide the missing object as the first argument\n\n"
                f"**ACTION REQUIRED**:\n"
                f"1. Check the function signature in {'the guardrail diagnostics' if has_signatures else 'the grounding source_excerpt'}\n"
                f"2. Identify what the FIRST parameter is and its type\n"
                f"3. Create that object and pass it when calling the function\n"
            )
        else:
            guidance.append(
                f"\n**ACTION REQUIRED**: Check the function signature and provide ALL required parameters.\n"
            )

    elif "signature_mismatch" in previous_feedback or "TypeError" in previous_feedback:
        has_signatures = bool(guardrail_context.get("signatures"))

        guidance.append(
            f"\n**SIGNATURE ERROR DETECTED**\n"
            f"You are calling a function incorrectly. Follow these steps:\n"
            f"1. Find the function signature in {'the guardrail diagnostics above' if has_signatures else 'the grounding source_excerpt'}\n"
            f"2. Check if it's an instance method (has 'self' as first parameter)\n"
            f"3. If instance method: Create the parent class instance FIRST\n"
            f"4. Count the required parameters and provide them ALL\n"
            f"5. Do NOT skip parameters or call methods directly that need 'self'\n"
        )

    elif "import" in previous_feedback.lower() and "cannot import name" in previous_feedback:
        guidance.append(
            f"\n**IMPORT ERROR DETECTED**\n"
            f"You're trying to import a class/function that doesn't exist.\n\n"
            f"**ACTION REQUIRED**:\n"
            f"1. Check the test_patch files in the commit_diff context - they show real imports that work\n"
            f"2. Look for import statements in test_patch_files to see what's actually available\n"
            f"3. If available, check module_introspection in guardrail context for available classes\n"
            f"4. Try importing the module itself and calling functions directly (e.g., 'import pylint.checkers.misc' then 'misc.function()')\n"
        )
    elif "import" in previous_feedback.lower():
        guidance.append(
            f"\n**IMPORT ERROR DETECTED**\n"
            f"Fix your imports. Ensure you're importing from the correct module.\n"
        )

    return "\n".join(guidance)


def _enforce_checklist(code: str, checklist: List[str]) -> Tuple[str, Dict[str, Any]]:
    coverage: Dict[str, List[str]] = {"missing": [], "checklist": checklist}
    lower_code = code.lower()
    for item in checklist:
        if not item:
            continue
        if item.lower() not in lower_code:
            coverage["missing"].append(item)
    if coverage["missing"]:
        comments = "\n".join(f"# Checklist TODO: {item}" for item in checklist if item)
        code = f"{comments}\n{code}"
    return code, coverage
