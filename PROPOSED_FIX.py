# Proposed changes to pytest_writer.py
# Add this new helper function to extract function signatures from source_excerpt

import re
from typing import Optional, Tuple

def _extract_function_signature_from_grounding(
    plan,
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
    grounding = plan.context.get("grounding", [])

    for item in grounding:
        source = item.get("source_excerpt", "")
        symbol = item.get("symbol", "")

        # If we have a target function, only process matching symbols
        if target_function and symbol != target_function:
            continue

        # Look for function definition
        # Pattern matches: def function_name( ... ): including multi-line signatures
        pattern = r'def\s+(\w+)\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*(?:->\s*[^:]+)?:'

        # For multi-line signatures, we need to be more careful
        # Look for 'def function_name(' and capture until we find '):'
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'def ' in line and (not target_function or target_function in line):
                # Found start of function definition
                signature_lines = [line]

                # Keep adding lines until we find the closing '):'
                j = i + 1
                while j < len(lines) and ')' not in signature_lines[-1]:
                    signature_lines.append(lines[j])
                    j += 1
                    if j - i > 20:  # Safety limit
                        break

                # Join and clean up the signature
                signature = '\n'.join(signature_lines)
                # Remove leading whitespace but preserve indentation structure
                signature = '\n'.join(l.strip() for l in signature_lines)

                return signature

    return None


def _build_signature_fix_guidance(
    previous_feedback: str,
    plan,
    guardrail_context: dict
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
    target_symbols = plan.context.get("target_symbols", [])
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
            elif 'linter' in first_param.lower():
                guidance_parts.append(
                    f"**ACTION REQUIRED:**\n"
                    f"1. Import and create a linter object: `from pylint.lint import PyLinter; linter = PyLinter()`\n"
                    f"2. Pass it as first argument: `{function_name}(linter, {missing_arg}, ...)`\n"
                )
            else:
                param_type = None
                type_match = re.search(r':\s*([^,\)=]+)', signature.split('(')[1].split(',')[0])
                if type_match:
                    param_type = type_match.group(1).strip()

                guidance_parts.append(
                    f"**ACTION REQUIRED:**\n"
                    f"1. The first parameter `{first_param}` has type: {param_type or 'see signature above'}\n"
                    f"2. Create an instance of that type\n"
                    f"3. Pass it as the first argument: `{function_name}({first_param}_instance, {missing_arg}, ...)`\n"
                )
    else:
        # Fallback to generic guidance
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


# MODIFIED VERSION of _build_feedback_guidance in pytest_writer.py
# Replace the section handling "missing 1 required positional argument"

def _build_feedback_guidance(
    previous_feedback: Optional[str],
    guardrail_context: dict,
    plan  # Add plan parameter to access grounding
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

    # ... rest of the function stays the same ...

    return "\n".join(guidance)


# SUMMARY OF CHANGES:
# 1. Add _extract_function_signature_from_grounding() helper
# 2. Add _build_signature_fix_guidance() for detailed signature error help
# 3. Modify _build_feedback_guidance() to use the new helpers
# 4. The changes ONLY affect "missing 1 required positional argument" errors
# 5. All other error types remain unchanged - won't affect astropy or requests
