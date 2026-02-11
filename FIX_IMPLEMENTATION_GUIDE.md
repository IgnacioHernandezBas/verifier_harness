# Implementation Guide: Fix for pylint-6506 Signature Mismatch Issue

## Problem Summary

**Instance:** `pylint-dev__pylint-6506`
**Error:** Stuck in loop with 3 identical `signature_mismatch` errors
**Root Cause:** LLM calls `_config_initialization(args_list)` but should call `_config_initialization(linter, args_list)`

## Why Current Feedback Fails

1. Python error says "missing 1 required positional argument: 'args_list'" - **MISLEADING**
2. The actual issue: missing the FIRST parameter (`linter`), not `args_list`
3. Current feedback doesn't extract the signature from grounding `source_excerpt`
4. LLM doesn't understand it needs to look at the grounding data

## Proposed Solution: Surgical, Targeted Fix

### What Changes

**File:** `agentic_closed_loop/pytest_writer.py`

**Changes:**
1. Add `_extract_function_signature_from_grounding()` - extracts signature from plan grounding
2. Add `_build_signature_fix_guidance()` - builds specific guidance with actual signature
3. Modify `_build_feedback_guidance()` to:
   - Accept `plan` parameter (to access grounding)
   - Call new helper for "missing 1 required positional argument" errors
   - Show extracted signature and specific fix

### Why This Won't Break Other Instances

| Aspect | Impact on Other Instances |
|--------|---------------------------|
| **Error Type Scope** | ONLY affects "missing 1 required positional argument" errors |
| **Other Errors Unchanged** | `fixture_missing`, `import_error`, `mocking_error`, `other` - NO CHANGES |
| **Fallback Behavior** | If signature extraction fails, uses existing generic guidance |
| **astropy-7746** | Had `fixture_missing` → `other` → `success`. Won't be affected. |
| **psf__requests-2148** | Had `import_error` → `mocking_error` → `success`. Won't be affected. |

### How It Helps pylint-6506

**Before (3 failed attempts):**
```
Previous attempt failed with signature_mismatch

**ERROR ANALYSIS**: The function is missing its FIRST parameter.
1. Check the function signature in the grounding source_excerpt
2. Identify what the FIRST parameter is and its type
3. Create that object and pass it when calling the function
```

**After (with new fix):**
```
Previous attempt failed with signature_mismatch

**⚠️ PYTHON ERROR MESSAGE IS MISLEADING!**
When Python says 'missing 1 required positional argument: args_list',
it often means you're passing args_list but missing the parameter BEFORE it.

**ACTUAL FUNCTION SIGNATURE FROM YOUR GROUNDING DATA:**
```python
def _config_initialization(
    linter: PyLinter,
    args_list: list[str],
    reporter: reporters.BaseReporter | reporters.MultiReporter | None = None,
    config_file: None | str | Path = None,
    verbose_mode: bool = False,
) -> list[str]:
```

**THE PROBLEM:**
- You're probably calling: `_config_initialization(args_list)`
- But the first parameter is: `linter`
- You need to call: `_config_initialization(linter, args_list, ...)`

**ACTION REQUIRED:**
1. Import and create a linter object: `from pylint.lint import PyLinter; linter = PyLinter()`
2. Pass it as first argument: `_config_initialization(linter, args_list, ...)`
```

## Implementation Steps

### Step 1: Update pytest_writer.py

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop
cp pytest_writer.py pytest_writer.py.backup
```

### Step 2: Add Helper Functions

Add these two functions at the top of `pytest_writer.py` (after imports):

```python
import re
from typing import Optional

def _extract_function_signature_from_grounding(
    plan,
    target_function: Optional[str] = None
) -> Optional[str]:
    """Extract function signature from grounding source_excerpt."""
    grounding = plan.context.get("grounding", [])

    for item in grounding:
        source = item.get("source_excerpt", "")
        symbol = item.get("symbol", "")

        if target_function and symbol != target_function:
            continue

        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'def ' in line and (not target_function or target_function in line):
                signature_lines = [line]

                j = i + 1
                while j < len(lines) and ')' not in signature_lines[-1]:
                    if j >= len(lines):
                        break
                    signature_lines.append(lines[j])
                    j += 1
                    if j - i > 20:  # Safety limit
                        break

                signature = '\n'.join(l.strip() for l in signature_lines)
                return signature

    return None


def _build_signature_fix_guidance(
    previous_feedback: str,
    plan,
    guardrail_context: dict
) -> str:
    """Build specific guidance for signature mismatch errors."""
    has_signatures = bool(guardrail_context.get("signatures"))
    guidance_parts = []

    # Extract missing arg from error
    missing_arg = None
    if "argument: " in previous_feedback:
        missing_arg = previous_feedback.split("argument: ")[1].split("\n")[0].strip("'\"")

    # Try to get function signature from grounding
    target_symbols = plan.context.get("target_symbols", [])
    function_name = target_symbols[0] if target_symbols else None

    signature = _extract_function_signature_from_grounding(plan, function_name)

    if signature and not has_signatures:
        guidance_parts.append(
            f"\n**⚠️ PYTHON ERROR MESSAGE IS MISLEADING!**\n"
            f"When Python says 'missing 1 required positional argument: {missing_arg}',\n"
            f"it often means you're passing {missing_arg} but missing the parameter BEFORE it.\n\n"
        )

        guidance_parts.append(
            f"**ACTUAL FUNCTION SIGNATURE FROM YOUR GROUNDING DATA:**\n"
            f"```python\n{signature}\n```\n\n"
        )

        # Parse first parameter
        first_param_match = re.search(r'def\s+\w+\s*\(\s*([^:,\)]+)', signature)
        if first_param_match:
            first_param = first_param_match.group(1).strip()

            guidance_parts.append(
                f"**THE PROBLEM:**\n"
                f"- You're probably calling: `{function_name}({missing_arg})`\n"
                f"- But the first parameter is: `{first_param}`\n"
                f"- You need to call: `{function_name}({first_param}, {missing_arg}, ...)`\n\n"
            )

            # Specific guidance based on parameter
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
            f"**ACTION REQUIRED**:\n"
            f"1. Check the function signature in {'the guardrail diagnostics' if has_signatures else 'the grounding source_excerpt'}\n"
            f"2. Identify what the FIRST parameter is and its type\n"
            f"3. Create that object and pass it when calling the function\n"
        )

    return '\n'.join(guidance_parts)
```

### Step 3: Modify _build_feedback_guidance

Find the function `_build_feedback_guidance` and:

1. **Add `plan` parameter:**
```python
def _build_feedback_guidance(
    previous_feedback: Optional[str],
    guardrail_context: Dict[str, Any],
    plan  # ADD THIS PARAMETER
) -> str:
```

2. **Replace the "missing 1 required positional argument" handler:**

Find this section (around line 146):
```python
if "missing 1 required positional argument" in previous_feedback:
    # Check if signature hints were available
    has_signatures = bool(guardrail_context.get("signatures"))

    # Extract the missing argument
    if "argument: " in previous_feedback:
        arg_part = previous_feedback.split("argument: ")[1].split("\n")[0].strip("'\"")
        guidance.append(
            f"\n**ERROR ANALYSIS**: The function is missing its FIRST parameter.\n"
            f"This usually means:\n"
            ...
```

Replace with:
```python
if "missing 1 required positional argument" in previous_feedback:
    # NEW: Use enhanced signature extraction and guidance
    sig_guidance = _build_signature_fix_guidance(
        previous_feedback,
        plan,
        guardrail_context
    )
    guidance.append(sig_guidance)
```

### Step 4: Update the Call Site

In `_build_extra_messages`, update the call to `_build_feedback_guidance`:

Find (around line 64):
```python
feedback_guidance = _build_feedback_guidance(previous_feedback, guardrail_context)
```

Change to:
```python
feedback_guidance = _build_feedback_guidance(previous_feedback, guardrail_context, plan)
```

## Testing the Fix

### 1. Test on pylint-6506 (the failing case)

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness

# Run just the pylint instance
python -m agentic_closed_loop.orchestrator \
  --state_file agentic_closed_loop/state/pylint-dev__pylint-6506_C1_RETEST.json \
  --instance_id pylint-dev__pylint-6506 \
  --claim_id C1 \
  --max_attempts 5 \
  --conda_env verifier_llm \
  --endpoint http://127.0.0.1:8000/v1 \
  --model Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
  --claims_dir claim_extraction/claims_out \
  --instances_file claim_extraction/instances.json \
  --tests_root claim_test_generation/tests_out \
  --claim_tests_root claim_test_generation/tests_out \
  --repos_root repos_claim_cache
```

**Expected outcome:** Should succeed within 5 attempts instead of getting stuck

### 2. Verify no regression on successful cases

Re-run a successful case to ensure it still works:

```bash
# Delete the old state to force fresh run
rm agentic_closed_loop/state/astropy__astropy-7746_C1_RETEST.json

python -m agentic_closed_loop.orchestrator \
  --state_file agentic_closed_loop/state/astropy__astropy-7746_C1_RETEST.json \
  --instance_id astropy__astropy-7746 \
  --claim_id C1 \
  --max_attempts 5 \
  --conda_env verifier_llm \
  --endpoint http://127.0.0.1:8000/v1 \
  --model Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
  --claims_dir claim_extraction/claims_out \
  --instances_file claim_extraction/instances.json \
  --tests_root claim_test_generation/tests_out \
  --claim_tests_root claim_test_generation/tests_out \
  --repos_root repos_claim_cache
```

**Expected outcome:** Should still succeed (probably same or fewer iterations)

## Rollback Plan

If the fix causes issues:

```bash
cd /fs/nexus-scratch/ihbas/verifier_harness/agentic_closed_loop
cp pytest_writer.py.backup pytest_writer.py
```

## Success Criteria

- [ ] pylint-dev__pylint-6506 succeeds within 5 attempts (currently fails at 3)
- [ ] astropy__astropy-7746 still succeeds (regression test)
- [ ] psf__requests-2148 still succeeds (regression test)
- [ ] No new error types introduced

## Additional Improvements (Future)

If this works well, we can add similar signature extraction for:
1. Other `TypeError` patterns
2. Instance method detection (self parameter)
3. Showing example usage from test_patch files
