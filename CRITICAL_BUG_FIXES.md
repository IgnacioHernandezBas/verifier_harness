# Critical Bug Fixes - Agentic Closed Loop

**Date**: 2026-02-18
**Status**: ✅ All fixes implemented and validated

## Summary

Fixed 3 critical bugs that were causing:
- 2 instances to waste all 10 attempts with incorrect feedback (django-16255, django-16408)
- Pattern detection to never run in the actual verification loop
- No early exit for repetitive failures

**Impact**: These fixes should improve success rate from ~24% to an estimated 35-45% by:
1. Providing accurate error classification
2. Enabling anti-pattern detection
3. Failing fast on stuck loops (saving compute time)

---

## Bug #1: Misclassification of Import Errors (HIGHEST PRIORITY)

### The Problem

**Location**: `agentic_closed_loop/diagnostics.py:128`

**What Was Wrong**:
The code checked if "_pytest" appeared ANYWHERE in error output, including pytest's own stack traces:
```python
if any(pattern in combined for pattern in ["_pytest", "from _", "._internal", "._private"]):
    return "internal_import_error", ...  # WRONG!
```

When a test had a legitimate import error (e.g., `ImportError: cannot import name 'get_latest_lastmod'`), the stack trace naturally includes paths like `.pip_packages/_pytest/python.py`, falsely triggering the internal import classification.

**Real-World Impact**:
- **django__django-16255**: Wasted 10 attempts with feedback about "_pytest imports" when the actual issue was trying to import a non-existent function `get_latest_lastmod`
- **django__django-16408**: Same issue - misdiagnosed for all 10 attempts
- LLM received completely wrong feedback, making learning impossible

### The Fix

**Files Changed**:
- `agentic_closed_loop/diagnostics.py` (lines 117-159)

**What Changed**:
1. Added `generated_code` parameter to `_classify_pair()` function
2. Use `detect_internal_import_attempt()` to check if the TEST CODE itself has internal imports
3. Only classify as `internal_import_error` if the code actually imports from `_pytest.*` or similar
4. For legitimate import errors, now provides enhanced guidance:
   - Extracts the specific symbol and module from error
   - Suggests checking grounding evidence
   - Recommends looking at test_patch files

**Code Changes**:
```python
# NEW: Check the actual test code, not just error output
has_internal_import_in_code = False
if generated_code:
    from .pattern_detector import detect_internal_import_attempt
    internal_import_pattern = detect_internal_import_attempt(generated_code)
    has_internal_import_in_code = internal_import_pattern is not None

if has_internal_import_in_code:
    return "internal_import_error", ...
# Otherwise, fall through to proper import_error classification
```

**Validation**: ✅ Test 1 & 2 pass - correctly distinguishes between real internal imports and false positives

---

## Bug #2: Pattern Detection Not Used in Verification Loop

### The Problem

**Location**: `agentic_closed_loop/run_agentic_loop_hybrid.py:461`

**What Was Wrong**:
The `classify_verification()` function accepts a `generated_code` parameter for anti-pattern detection, but it was NEVER passed in the actual verification loop:
```python
diagnosis = diagnostics.classify_verification(result)  # Missing generated_code!
```

This meant:
- Pattern detection code existed but was unused
- Fixture misuse patterns were never detected
- Internal import detection was skipped

### The Fix

**Files Changed**:
- `agentic_closed_loop/run_agentic_loop_hybrid.py` (lines 455-475)
- `agentic_closed_loop/diagnostics.py` (line 318 - updated to pass parameter through)

**What Changed**:
```python
# NEW: Extract generated code from last attempt
attempts = state["attempts"]
generated_code = ""
if attempts:
    last_attempt = attempts[-1]
    generated_code = last_attempt.get("generated_code", "")

# Pass it to classification
diagnosis = diagnostics.classify_verification(result, generated_code=generated_code)
```

Also updated `classify_verification()` to pass the code to `_classify_pair()`:
```python
label, details = _classify_pair(tests[0]["bug"], tests[0]["gold"], generated_code=generated_code or "")
```

**Validation**: ✅ Test 3 passes - pattern detection now works correctly

---

## Bug #3: No Early Exit for Repetitive Failures

### The Problem

**Location**: `agentic_closed_loop/orchestrator.py:248-251`

**What Was Wrong**:
The orchestrator checks for stuck loops after 3 attempts and exits early for specific error types:
```python
if error_label in [
    "signature_mismatch", "import_error", "fixture_missing",
    "signature_check", "import_check_failed", "probe_check_failed"
]:
    return {"should_exit": True, "reason": "stuck_in_loop"}
```

But `"internal_import_error"` was NOT in this list! This caused:
- 2 instances (django-16255, django-16408) to waste 7 extra attempts with identical errors
- Unnecessary compute cost
- No benefit since LLM wasn't learning

### The Fix

**Files Changed**:
- `agentic_closed_loop/orchestrator.py` (lines 244-256)

**What Changed**:
Added missing error types to the early-exit list:
```python
if error_label in [
    "signature_mismatch", "import_error", "fixture_missing",
    "signature_check", "import_check_failed", "probe_check_failed",
    "internal_import_error",  # FIX: Was missing
    "mocking_error",          # Also exit on repeated mocking issues
    "environment_error"       # Environment issues won't be fixed by retrying
]:
```

**Validation**: ✅ Test 4 passes - would exit after 3 identical errors

---

## Testing

### Test File
Created: `agentic_closed_loop/test_bug_fixes.py`

### Test Results
```
✅ PASSED: Bug #1: Misclassification Fix
✅ PASSED: Bug #1: Real Internal Imports
✅ PASSED: Bug #2: Pattern Detection
✅ PASSED: Bug #3: Early Exit

Total: 4/4 tests passed
```

### How to Run Tests
```bash
python -m agentic_closed_loop.test_bug_fixes
```

---

## Expected Impact

### Before Fixes (Meta Llama 70B Results)
- **Success Rate**: 23.5% (4/17)
- **Max Attempts Hit**: 52.9% (9/17)
- **UNRESOLVED Cases**: 2 instances wasted 20 attempts total

### After Fixes (Projected)
- **Success Rate**: 35-45% (estimated 6-8 successes)
- **Max Attempts Hit**: 30-40% (faster failure on stuck loops)
- **UNRESOLVED Cases**: Should fail fast after 3 attempts (saving 14 attempts)

### Specific Instance Improvements

**django__django-16255** (UNRESOLVED → Likely SUCCESS):
- Before: 10 attempts, all with wrong "internal_import_error" feedback
- After: Should get correct "import_error: cannot import 'get_latest_lastmod'" feedback
- LLM can now learn to fix the actual import issue

**django__django-16408** (UNRESOLVED → Likely FAIL FAST):
- Before: 10 attempts with wrong feedback
- After: Will get correct diagnosis and fail fast after 3 attempts if stuck
- Saves 7 attempts worth of compute

---

## Files Modified

1. **agentic_closed_loop/diagnostics.py**
   - Lines 117-159: Fixed `_classify_pair()` to check actual test code
   - Line 318: Pass `generated_code` to `_classify_pair()`

2. **agentic_closed_loop/run_agentic_loop_hybrid.py**
   - Lines 455-475: Extract and pass `generated_code` to `classify_verification()`

3. **agentic_closed_loop/orchestrator.py**
   - Lines 244-256: Added missing error types to early-exit list

4. **agentic_closed_loop/test_bug_fixes.py** (NEW)
   - Comprehensive validation tests for all 3 fixes

---

## Backward Compatibility

✅ **Fully backward compatible**
- All changes are internal improvements
- No API changes
- Existing state files will work correctly
- No configuration changes needed

---

## Next Steps (Recommended)

### Immediate
1. ✅ Run validation tests (done)
2. 🔄 Test on a small batch (2-3 previously failed instances)
3. 🔄 Monitor results for improvements

### Short Term (This Week)
1. Add reflection step before retry (see analysis document)
2. Scale feedback intensity with attempt number
3. Add API discovery with `dir(module)` introspection

### Medium Term (Next Week)
1. Implement diff-style error feedback
2. Extract and show test_patch imports more prominently
3. Consider model ensemble: Opus for planning, Llama for iteration

---

## Validation Commands

```bash
# Run the test suite
python -m agentic_closed_loop.test_bug_fixes

# Test on a single previously-failed instance
sbatch --export=INSTANCE_ID=django__django-16255,MAX_ATTEMPTS=4 \
  agentic_closed_loop/scripts_slurm/run_agentic_loop_hybrid_multiple.sbatch

# Compare results
python agentic_closed_loop/batch_summarize_results.py
```

---

## Notes

- All fixes focus on accurate classification and early failure detection
- No changes to prompts or generation logic (yet)
- Pattern detection was already implemented, just not activated
- Early exit logic was already implemented, just missing some error types

**The fixes are surgical and low-risk - they make the existing system work as intended.**

---

## Credits

- Analysis performed: 2026-02-18
- Fixes implemented: 2026-02-18
- Validation completed: 2026-02-18
- All tests passing ✅
