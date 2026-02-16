from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claim_test_generation.claim_test_generator import (
    VLLMClient,
    generate_pytest_for_claim,
)

from .example_extractor import (
    extract_fixture_usage_examples,
    extract_import_patterns,
    extract_claim_keywords,
)
from .pattern_detector import detect_fixture_misuse
from .planner import Plan, plan_to_messages
from .test_sketcher import TestSketch


def _extract_function_signature_from_grounding(
    plan: Plan,
    target_function: Optional[str] = None
) -> Optional[str]:
    """
    Extract function signature from grounding source_excerpt.

    Args:
        plan: The plan object containing grounding info
        target_function: Specific function name to look for (if None, looks for first 'def')

    Returns:
        Function signature string or None if not found
    """
    grounding = getattr(plan.context, "grounding", [])

    for item in grounding:
        # GroundingEvidence is a dataclass, not a dict
        source = getattr(item, "source_excerpt", "")
        symbol = getattr(item, "symbol", "")

        # If we have a target function, only process matching symbols
        if target_function and symbol != target_function:
            continue

        # Look for function definition - capture multi-line signatures
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'def ' in line and (not target_function or target_function in line):
                # Found start of function definition
                signature_lines = [line]

                # Keep adding lines until we find the closing ')' and ':'
                # which marks the end of a function signature
                j = i + 1
                while j < len(lines):
                    if j >= len(lines):
                        break
                    # Check if this line contains the closing parenthesis
                    # Could be '):' or ') -> type:' pattern
                    stripped = lines[j].strip()
                    if stripped.startswith(')') and ':' in stripped:
                        signature_lines.append(lines[j])
                        break
                    signature_lines.append(lines[j])
                    j += 1
                    if j - i > 20:  # Safety limit
                        break

                # Join and clean up the signature
                signature = '\n'.join(l.strip() for l in signature_lines)
                return signature

    return None


def _build_signature_fix_guidance(
    previous_feedback: str,
    plan: Plan,
    guardrail_context: Dict[str, Any]
) -> str:
    """
    Build specific guidance for signature mismatch errors.
    Extracts actual signature from grounding and shows what needs to be fixed.
    """
    has_signatures = bool(guardrail_context.get("signatures"))
    guidance_parts = []

    # Extract the missing argument from error message
    missing_arg = None
    if "argument: " in previous_feedback:
        missing_arg = previous_feedback.split("argument: ")[1].split("\n")[0].strip("'\"")

    # Try to extract function signature from grounding
    target_symbols = getattr(plan.context, "target_symbols", [])
    function_name = target_symbols[0] if target_symbols else None

    signature = _extract_function_signature_from_grounding(plan, function_name)

    if signature and not has_signatures:
        # We found the signature in grounding and guardrails don't have it
        guidance_parts.append(
            f"\n**⚠️ PYTHON ERROR MESSAGE IS MISLEADING!**\n"
            f"When Python says 'missing 1 required positional argument: {missing_arg}',\n"
            f"it often means you're passing {missing_arg} but missing the parameter BEFORE it.\n\n"
        )

        guidance_parts.append(
            f"**ACTUAL FUNCTION SIGNATURE FROM YOUR GROUNDING DATA:**\n"
            f"```python\n{signature}\n```\n\n"
        )

        # Parse the signature to identify the first parameter
        first_param_match = re.search(r'def\s+\w+\s*\(\s*([^:,\)]+)', signature)
        if first_param_match:
            first_param = first_param_match.group(1).strip()

            guidance_parts.append(
                f"**THE PROBLEM:**\n"
                f"- You're probably calling: `{function_name}({missing_arg})`\n"
                f"- But the first parameter is: `{first_param}`\n"
                f"- You need to call: `{function_name}({first_param}, {missing_arg}, ...)`\n\n"
            )

            # Provide specific guidance based on parameter name
            if first_param == 'self':
                guidance_parts.append(
                    f"**ACTION REQUIRED:**\n"
                    f"1. Find the class that contains `{function_name}`\n"
                    f"2. Create an instance of that class first\n"
                    f"3. Call the method on that instance: `obj.{function_name}({missing_arg})`\n"
                )
            else:
                guidance_parts.append(
                    f"**ACTION REQUIRED:**\n"
                    f"1. The first parameter is `{first_param}` - create an instance of this type\n"
                    f"2. Pass it as the first argument: `{function_name}({first_param}_instance, {missing_arg}, ...)`\n"
                )
    else:
        # Fallback to existing generic guidance
        guidance_parts.append(
            f"\n**ERROR ANALYSIS**: The function is missing its FIRST parameter.\n"
            f"This usually means:\n"
            f"1. If the error mentions 'self', you need to create an instance of the parent class\n"
            f"2. Otherwise, you need to create/provide the missing object as the first argument\n\n"
            f"**ACTION REQUIRED**:\n"
            f"1. Check the function signature in {'the guardrail diagnostics' if has_signatures else 'the grounding source_excerpt'}\n"
            f"2. Identify what the FIRST parameter is and its type\n"
            f"3. Create that object and pass it when calling the function\n"
        )

    return '\n'.join(guidance_parts)


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
    previous_code: Optional[str] = None,
    previous_patterns: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Dict[str, Any]]:
    extra_messages = _build_extra_messages(
        plan=plan,
        sketch=sketch,
        guardrail_context=guardrail_context,
        guardrail_checks=guardrail_checks,
        previous_feedback=previous_feedback,
        previous_code=previous_code,
        previous_patterns=previous_patterns,
    )
    code = generate_pytest_for_claim(
        claim,
        repo=sample.get("repo", "unknown_repo"),
        instance_id=plan.instance_id,
        client=client,
        extra_messages=extra_messages,
        test_patch=sample.get("test_patch"),
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
    previous_code: Optional[str] = None,
    previous_patterns: Optional[List[Dict[str, Any]]] = None,
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
    feedback_guidance = _build_feedback_guidance(
        previous_feedback, guardrail_context, plan, previous_code, previous_patterns
    )

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
    previous_feedback: Optional[str],
    guardrail_context: Dict[str, Any],
    plan: Plan,
    previous_code: Optional[str] = None,
    previous_patterns: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build guidance based on previous failure feedback."""
    if not previous_feedback:
        return ""

    guidance = ["## CRITICAL: Learn from Previous Failure\n"]
    guidance.append(f"Previous attempt failed with:\n```\n{previous_feedback}\n```\n")

    # Detect specific error patterns and provide targeted advice
    if "missing 1 required positional argument" in previous_feedback:
        # NEW: Use enhanced signature extraction and guidance
        sig_guidance = _build_signature_fix_guidance(
            previous_feedback,
            plan,
            guardrail_context
        )
        guidance.append(sig_guidance)

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

    elif "internal_import_error" in previous_feedback or (
        "internal/private module" in previous_feedback.lower()
    ):
        guidance.append(
            _build_internal_import_guidance(plan, previous_code, previous_patterns)
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


def _build_internal_import_guidance(
    plan: Plan,
    previous_code: Optional[str],
    previous_patterns: Optional[List[Dict[str, Any]]],
) -> str:
    """
    Build guidance for internal import errors using repo examples.

    Detects specific anti-patterns and provides repo-specific examples when available.

    Args:
        plan: The test plan with context
        previous_code: The previously generated code
        previous_patterns: Detected anti-patterns from diagnostics

    Returns:
        Guidance string with repo examples or generic fallback
    """
    guidance_parts = []

    # Detect what went wrong
    fixture_misuse = None
    if previous_code:
        fixture_misuse = detect_fixture_misuse(previous_code)
    elif previous_patterns:
        fixture_misuse = next(
            (p for p in previous_patterns if p.get("pattern") == "fixture_attribute_error"),
            None
        )

    if fixture_misuse:
        fixture_name = fixture_misuse.get("fixture_name", "tmpdir_factory")

        # Extract claim keywords to avoid leakage
        claim_keywords = extract_claim_keywords(
            getattr(plan.context, "claim_text", ""),
            getattr(plan.context, "given", ""),
            getattr(plan.context, "when", "")
        )

        # Try to get repo-specific examples
        commit_diff = getattr(plan.context, "commit_diff", None)
        test_files = getattr(commit_diff, "test_patch_files", []) if commit_diff else []
        repo_path_str = getattr(plan.context, "repo_path", "")
        repo_path = Path(repo_path_str) if repo_path_str else None

        example = None
        if repo_path and repo_path.exists() and test_files:
            example = extract_fixture_usage_examples(
                repo_path=repo_path,
                test_files=test_files,
                fixture_name=fixture_name,
                claim_keywords=claim_keywords
            )

        if example:
            guidance_parts.append(
                f"\n**🚨 FIXTURE USAGE ERROR 🚨**\n"
                f"You tried: `pytest.{fixture_name}` (WRONG - this doesn't exist)\n"
                f"Fixtures are function parameters, not module attributes!\n\n"
                f"{example}\n\n"
                f"**YOUR FIX:**\n"
                f"```python\n"
                f"def test_claim_c1({fixture_name}):  # ← Add as parameter\n"
                f"    result = {fixture_name}.mktemp('foo')  # ← Use directly\n"
                f"```\n\n"
                f"**KEY POINT**: Fixtures are injected by pytest when you add them as parameters.\n"
                f"You CANNOT access them via pytest.{fixture_name} - that doesn't exist!\n"
            )
        else:
            # Fallback to generic fixture guidance
            guidance_parts.append(_generic_fixture_guidance(fixture_name))
    else:
        # Generic internal import error
        guidance_parts.append(_generic_internal_import_guidance())

    return '\n'.join(guidance_parts)


def _generic_fixture_guidance(fixture_name: str) -> str:
    """Fallback guidance when no repo examples available."""
    return (
        f"\n**🚨 FIXTURE USAGE ERROR 🚨**\n"
        f"You tried to use '{fixture_name}' incorrectly.\n\n"
        f"**WRONG APPROACHES**:\n"
        f"❌ pytest.{fixture_name}  # Doesn't exist!\n"
        f"❌ from _pytest import {fixture_name}  # Internal module not available!\n\n"
        f"**CORRECT APPROACH**:\n"
        f"✅ Add '{fixture_name}' as a function parameter:\n"
        f"```python\n"
        f"def test_claim_c1({fixture_name}):  # ← Add as parameter\n"
        f"    # Now you can use {fixture_name} directly\n"
        f"    result = {fixture_name}.method(...)\n"
        f"```\n\n"
        f"**HOW PYTEST FIXTURES WORK**:\n"
        f"1. Fixtures are NOT imported - they're injected by pytest\n"
        f"2. Add the fixture name as a parameter to your test function\n"
        f"3. Pytest automatically creates and passes the fixture object\n"
        f"4. Use the fixture directly in your test body\n"
    )


def _generic_internal_import_guidance() -> str:
    """Fallback guidance for general internal imports."""
    return (
        f"\n**🚨 CRITICAL: INTERNAL MODULE IMPORT ERROR 🚨**\n"
        f"You are importing from INTERNAL/PRIVATE modules that are NOT available!\n\n"
        f"**ROOT CAUSE**:\n"
        f"- You used imports like: from _pytest.tmpdir import TempdirFactory\n"
        f"- Internal modules (starting with _) are NOT available in the test environment\n"
        f"- This causes ModuleNotFoundError or ImportError\n\n"
        f"**MANDATORY FIX - Rewrite your test using ONLY public APIs**:\n"
        f"1. ✅ Use: import pytest\n"
        f"2. ✅ Use pytest's built-in fixtures:\n"
        f"      - tmpdir or tmp_path (for temporary directories)\n"
        f"      - tmpdir_factory or tmp_path_factory (for factory objects)\n"
        f"      - monkeypatch (for mocking)\n"
        f"      - capsys, capfd (for capturing output)\n"
        f"3. ❌ REMOVE all imports from _pytest.*, _internal.*, or any _private.* modules\n\n"
        f"**CONCRETE EXAMPLES**:\n"
        f"❌ BAD:  from _pytest.tmpdir import TempdirFactory\n"
        f"         def test(): factory = TempdirFactory(...)\n"
        f"✅ GOOD: def test(tmpdir_factory):  # Use pytest's built-in fixture\n"
        f"         temp_dir = tmpdir_factory.mktemp('sub')\n\n"
        f"❌ BAD:  from _pytest.monkeypatch import MonkeyPatch\n"
        f"✅ GOOD: def test(monkeypatch):  # Use pytest's built-in fixture\n\n"
        f"❌ BAD:  import pytest; pytest.tmpdir_factory.mktemp('foo')\n"
        f"✅ GOOD: def test(tmpdir_factory): tmpdir_factory.mktemp('foo')\n\n"
        f"**YOUR NEXT ATTEMPT MUST**:\n"
        f"- Remove ALL imports starting with underscore (_pytest, _internal, etc.)\n"
        f"- Use pytest fixtures as function parameters\n"
        f"- Test through public interfaces only\n"
    )


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
