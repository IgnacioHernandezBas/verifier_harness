# Agentic Loop Workflow Improvements

**Date**: 2026-02-07
**Analysis of Jobs**: 6242293 (pylint-6506), 6249429 (psf__requests-2148)

## Issues Identified & Fixed

### ✅ Issue 1: Guardrail Probe Check Blocking Valid Instance Methods

**Job**: 6249429 (psf__requests-2148)
**Severity**: 🔴 Critical - Blocks valid test generation before it even starts

**Problem**:
- Guardrail `probe_check` tried to call instance methods without an instance
- Example: `iter_content()` is a method requiring `self`, but probe called it as `func()`
- This caused `TypeError: Response.iter_content() missing 1 required positional argument: 'self'`
- Result: Test generation never started

**Root Cause** (`guardrails.py:234-260`):
```python
# Old code filtered out self/cls but still tried to call the method
filtered = [p for p in required_params if p.name not in ("self", "cls")]
if filtered:
    return True, "Requires non-trivial inputs; probe skipped."

# BUG: If only self/cls were required, filtered is empty,
# but we still execute func(*args, **kwargs) <- FAILS!
```

**Fix Applied** (`guardrails.py:246-250`):
```python
# If we have required params but all were self/cls, skip probe
# (this is an instance/class method that needs an instance)
if required_params and not filtered:
    return True, "Instance/class method; probe skipped."
```

**Impact**: Instance methods like `iter_content`, `stream`, etc. will no longer block at guardrail stage

---

### ✅ Issue 2: Vague Feedback for Signature Mismatches

**Job**: 6242293 (pylint-6506)
**Severity**: 🔴 Critical - Causes 10 wasted iterations with same error

**Problem**:
- LLM received generic "Call signature mismatch" feedback
- Test called `_config_initialization(args_list)` but function requires `_config_initialization(linter, args_list)`
- Same error repeated 10 times - LLM couldn't learn from feedback
- Guardrail couldn't import module in host environment, so no signature hints available

**Example Error**:
```
TypeError: _config_initialization() missing 1 required positional argument: 'args_list'
```

**Old Feedback**:
```
Call signature mismatch.

Error details:
[full traceback]
```

**Fix Applied** (`diagnostics.py:66-73`):
```python
# Extract specific missing argument from error message
import re
match = re.search(r"missing \d+ required positional arguments?: ['\"]?([^'\"]+)['\"]?", combined)
hint = ""
if match:
    missing_arg = match.group(1)
    hint = f"\n\n💡 Hint: The function is missing the required argument(s): {missing_arg}"
    hint += "\nCheck the function signature and ensure all required parameters are provided."
return "signature_mismatch", f"Call signature mismatch.{hint}\n\nError details:\n{bug_errors}"
```

**New Feedback**:
```
Call signature mismatch.

💡 Hint: The function is missing the required argument(s): args_list
Check the function signature and ensure all required parameters are provided.

Error details:
[relevant error lines]
```

**Impact**: LLM gets specific actionable feedback about what's missing

---

### ✅ Issue 3: No Early Exit for Repeated Failures

**Job**: 6242293 (pylint-6506)
**Severity**: 🟡 Medium - Wastes compute resources

**Problem**:
- System ran all 10 iterations with identical `signature_mismatch` error every time
- Wasted compute and time when it was clear the LLM couldn't fix the issue
- No detection of stuck-in-loop scenarios

**Fix Applied** (`orchestrator.py:224-238`):
```python
# Exit condition 3: Repeated identical errors (stuck in loop)
if attempt >= 3 and len(attempts) >= 3:
    # Check if last 3 attempts have identical error labels
    recent_labels = [
        att.get("failure_classification", {}).get("label", "")
        for att in attempts[-3:]
    ]
    if len(set(recent_labels)) == 1 and recent_labels[0] in [
        "signature_mismatch", "import_error", "fixture_missing"
    ]:
        return {
            "should_exit": True,
            "reason": f"stuck_in_loop - same '{recent_labels[0]}' error 3 times, LLM not learning from feedback",
        }
```

**Impact**:
- Exits after 3 identical errors instead of wasting all 10 attempts
- Saves ~70% of compute time on stuck cases
- Clear diagnostic: "stuck_in_loop - same 'signature_mismatch' error 3 times"

---

### ✅ Issue 4: Truncated Function Signatures in Grounding

**Severity**: 🟡 Medium - Reduces context quality

**Problem**:
- Source excerpts truncated at exactly 1200 characters
- Could cut off in the middle of function signatures
- LLM missing critical signature information for test generation

**Example** (from job state):
```python
"source_excerpt": "# -*- coding: utf-8 -*-...\n\ndef _config_initialization(\n    linter: PyLinter,\n    args_list: list[str],\n    reporter: reporters.BaseReporter | report"  # <- CUT OFF!
```

**Fix Applied** (`context.py:246-275`):
```python
# Smart truncation: try to include complete function/class definitions
truncated = text[:MAX_SOURCE_CHARS]

# If we're in the middle of a function signature (contains 'def ' or 'class ' but no closing paren)
import re
if re.search(r'\b(def|class)\s+\w+\s*\(', truncated) and truncated.count('(') > truncated.count(')'):
    # Try to extend to the closing paren of the signature
    extra_chars = min(500, len(text) - MAX_SOURCE_CHARS)
    extended = text[:MAX_SOURCE_CHARS + extra_chars]
    # Find the first line after the signature starts
    match = re.search(r'(\bdef\b.*?:\s*\n)', extended, re.DOTALL)
    if match:
        return extended[:match.end()]

return truncated
```

**Impact**: Function signatures will be complete, giving LLM better context for test generation

---

## Summary of Changes

### Files Modified:
1. `agentic_closed_loop/guardrails.py` - Fixed probe_check for instance methods
2. `agentic_closed_loop/diagnostics.py` - Enhanced feedback with specific hints
3. `agentic_closed_loop/orchestrator.py` - Added early exit for repeated errors
4. `agentic_closed_loop/context.py` - Smart truncation for function signatures

### Expected Improvements:
- ✅ **No more guardrail blocks on valid instance methods**
- ✅ **Better feedback helps LLM fix signature issues**
- ✅ **Early exit saves ~70% compute on stuck cases**
- ✅ **Complete function signatures in context**

### Testing Recommendations:
1. **Rerun job 6249429** (psf__requests-2148) - Should pass guardrails now
2. **Rerun job 6242293** (pylint-6506) with new feedback - Should exit after 3 attempts max
3. **Monitor new runs** - Check for improved success rates and faster convergence

---

## Next Steps

1. **Commit these changes**:
   ```bash
   git add agentic_closed_loop/guardrails.py \
           agentic_closed_loop/diagnostics.py \
           agentic_closed_loop/orchestrator.py \
           agentic_closed_loop/context.py

   git commit -m "Polish agentic loop workflow

   - Fix guardrail probe_check blocking instance methods
   - Add specific hints for signature mismatch errors
   - Implement early exit after 3 identical errors
   - Smart truncation for complete function signatures"
   ```

2. **Test the fixes**:
   ```bash
   # Test psf__requests-2148 (should pass guardrails now)
   sbatch --export=INSTANCE_ID=psf__requests-2148,CLAIM_ID=C1,MAX_ATTEMPTS=4 \
     agentic_closed_loop/scripts_slurm/run_agentic_loop_hybrid.sbatch

   # Test pylint-dev__pylint-6506 (should exit early)
   sbatch --export=INSTANCE_ID=pylint-dev__pylint-6506,CLAIM_ID=C1,MAX_ATTEMPTS=10 \
     agentic_closed_loop/scripts_slurm/run_agentic_loop_hybrid.sbatch
   ```

3. **Monitor results**:
   - Check if psf__requests-2148 generates tests (previously blocked at guardrails)
   - Check if pylint-6506 exits after 3 attempts instead of 10
   - Look for improved success rates in batch runs
