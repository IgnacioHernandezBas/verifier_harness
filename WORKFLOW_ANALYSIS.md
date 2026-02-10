# Agentic Hybrid Workflow Analysis
## Analysis Date: 2026-02-09

This document analyzes critical issues found in jobs 6242293 and 6249429.

---

## Issue #1: Non-Learning Iterative Loop (Job 6242293 - pylint-dev__pylint-6506)

### Problem
The workflow ran **all 10 iterations** with the **exact same error** every time:
```
TypeError: _config_initialization() missing 1 required positional argument: 'args_list'
```

### Root Causes

1. **Incorrect Function Call Pattern**
   - **Actual signature** (from grounding data):
     ```python
     def _config_initialization(
         linter: PyLinter,
         args_list: list[str],
         reporter: reporters.BaseReporter | reporters.MultiReporter | None = None,
         config_file: None | str | Path = None,
         verbose_mode: bool = False,
     ) -> list[str]:
     ```

   - **Generated test calls it as**:
     ```python
     _config_initialization(args_list)  # WRONG! Missing linter parameter
     ```

   - **Should be**:
     ```python
     from pylint.lint import PyLinter
     linter = PyLinter()
     _config_initialization(linter, args_list)  # CORRECT
     ```

2. **Agent Not Using Grounding Information**
   - The signature IS provided in the grounding data (line 37 of state file)
   - The agent sees it but doesn't understand how to use it
   - The LLM doesn't understand it needs to create a `PyLinter` instance first

3. **No Learning from Feedback**
   - Feedback provided: `"signature_mismatch: Call signature mismatch...TypeError: _config_initialization() missing 1 required positional argument: 'args_list'"`
   - Agent receives feedback but generates identical broken code
   - Line numbers change (15→20→11→15) but logic stays the same
   - **The prompt/instructions don't guide the agent to introspect code or adapt**

4. **Early Stopping Logic NOT Triggered**
   - The orchestrator HAS early stopping logic (lines 231-244 in orchestrator.py):
     ```python
     if attempt >= 3 and len(attempts) >= 3:
         recent_labels = [...]
         if len(set(recent_labels)) == 1 and recent_labels[0] in [
             "signature_mismatch", "import_error", "fixture_missing"
         ]:
             return {"should_exit": True, "reason": "stuck_in_loop..."}
     ```
   - **BUT: Job 6242293 is NOT using the orchestrator!**
   - It's using the old `run_agentic_loop.py` which runs full 10 iterations without early stopping
   - The `.sbatch` script needs to be updated to use `orchestrator.py`

---

## Issue #2: Guardrail Probe Check Failures (Job 6249429 - psf__requests-2148)

### Problem
The workflow fails **immediately** at the guardrail stage:
```json
{
  "probe_check": {
    "passed": false,
    "details": {
      "failures": [
        "iter_content: Raised TypeError: Response.iter_content() missing 1 required positional argument: 'self'"
      ]
    }
  }
}
```

### Root Cause

**Guardrail probe is calling instance methods incorrectly**

In `guardrails.py`, function `_execute_probe` (lines 234-265):

```python
def _execute_probe(symbol: str, func: Any) -> Tuple[bool, str]:
    # ... signature inspection ...

    # Logic to skip instance methods (lines 254-257)
    if required_params and not filtered:
        return True, "Instance/class method; probe skipped."

    # If not skipped, try to call it (lines 259-265)
    args = []
    kwargs = {}
    try:
        func(*args, **kwargs)  # ❌ FAILS for instance methods!
    except Exception as exc:
        return False, f"Raised {exc.__class__.__name__}: {exc}"
```

**The skip logic SHOULD work but doesn't:**
- For `iter_content(self, chunk_size=1, decode_unicode=False)`
- `required_params` should include `self`
- `filtered` should be empty (self is filtered out)
- `if required_params and not filtered:` should be True → skip
- **But the probe is still executing and failing!**

**Possible causes:**
1. The `func` object being passed is not preserving the signature correctly
2. When retrieving via `getattr(class_obj, 'iter_content')`, the signature might be malformed
3. The logic at line 256 might have a subtle bug (e.g., empty list evaluation)

---

## Issue #3: Missing Context for Instance Method Testing

### Problem
Even if tests are generated, they lack proper setup for instance methods.

**Example**: To test `Response.iter_content()`, you need:
```python
import requests

# Create a Response instance
response = requests.Response()

# Mock the raw stream
class MockRaw:
    def stream(self, chunk_size, decode_content=None):
        raise socket.error("Connection reset")

response.raw = MockRaw()

# NOW you can test
with pytest.raises(requests.exceptions.ConnectionError):
    list(response.iter_content())
```

**Current approach**: Tries to call `iter_content()` directly without a Response instance.

**The agent needs**:
1. Recognition that methods need instances
2. Knowledge of how to construct those instances
3. Ability to create mocks/fixtures for complex setups

---

## Recommendations

### 1. Fix Guardrail Probe Logic (CRITICAL)

**File**: `agentic_closed_loop/guardrails.py`

**Current Issue**: Lines 254-257 should skip instance methods but don't

**Debug Steps**:
1. Add logging to see what `required_params` and `filtered` actually contain
2. Check if the function object signature is being preserved correctly
3. Verify that `getattr(class_obj, symbol)` returns the right object

**Potential Fix**:
```python
def _execute_probe(symbol: str, func: Any) -> Tuple[bool, str]:
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return True, "Signature unavailable; skipping probe."

    params = list(sig.parameters.values())

    # Check if this looks like an instance/class method
    if params and params[0].name in ('self', 'cls'):
        return True, "Instance/class method; probe skipped."

    # Check for other required params
    required = [p for p in params
                if p.default is inspect._empty
                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]

    if required:
        return True, "Requires non-trivial inputs; probe skipped."

    # Safe to probe
    try:
        func()
    except Exception as exc:
        return False, f"Raised {exc.__class__.__name__}: {exc}"
    return True, "Probe succeeded."
```

### 2. Improve Agent Prompting (CRITICAL)

**File**: `agentic_closed_loop/pytest_writer.py` or prompt templates

**Add explicit instructions**:

```
When generating tests for instance methods:
1. Check the function signature - does it have 'self' or 'cls' as first parameter?
2. If yes, you MUST create an instance of the parent class first
3. Look at the grounding data for the full signature
4. If you see "Response.iter_content(self, ...)", you need:
   - Import the Response class
   - Create an instance: `response = Response()`
   - Call the method: `response.iter_content(...)`

When you receive feedback about "missing required positional argument":
1. READ the error carefully - which argument is missing?
2. CHECK the function signature in the grounding data
3. CREATE any required objects (linters, responses, etc.)
4. RETRY with the correct calling pattern

Example error: "_config_initialization() missing 1 required positional argument: 'args_list'"
This means the FIRST parameter is missing (before args_list).
Check signature: _config_initialization(linter: PyLinter, args_list: list[str], ...)
Solution: Create a PyLinter instance first!
```

### 3. Use Orchestrator for All Jobs (IMMEDIATE)

**File**: `agentic_closed_loop/scripts_slurm/run_agentic_loop.sbatch`

**Current**: Calls `run_agentic_loop.py` directly
**Should**: Call `orchestrator.py` instead

**Benefits**:
- Early stopping when stuck (after 3 identical errors)
- Better feedback handling
- Cleaner state management

**Update**:
```bash
# Old:
python -m agentic_closed_loop.run_agentic_loop --instance ...

# New:
python -m agentic_closed_loop.orchestrator --instance ...
```

### 4. Enhance Signature Hints in Guardrails (MEDIUM)

**File**: `agentic_closed_loop/guardrails.py`

**Current**: Provides raw signature strings
**Should**: Provide instance creation hints

**Enhancement**:
```python
def _run_signature_check(...):
    # ... existing code ...

    for symbol in plan.target_symbols:
        attr = getattr(module, symbol, None)
        owner_class = None

        if attr is None:
            for class_name, class_obj in module_classes.items():
                if hasattr(class_obj, symbol):
                    owner_class = class_obj
                    owner_name = class_name
                    attr = getattr(class_obj, symbol)
                    break

        # ... signature extraction ...

        if owner_class and inspect.ismethod(attr):
            # Add instantiation hint
            signature_hints[symbol]["needs_instance"] = True
            signature_hints[symbol]["class_name"] = owner_name
            signature_hints[symbol]["instantiation_example"] = (
                f"{owner_name}() # May need constructor arguments"
            )
```

### 5. Add Code Inspection Capability (MEDIUM)

**Allow agent to READ source code when stuck**

When feedback indicates a signature error:
1. Agent should read the actual source file
2. Find the function definition
3. Understand the signature
4. Generate correct calling pattern

**Implementation**:
```python
def handle_signature_error(feedback, context):
    if "missing 1 required positional argument" in feedback:
        # Extract function name from error
        func_name = extract_function_name(feedback)

        # Read source file
        source_path = context.primary_path
        with open(source_path) as f:
            source = f.read()

        # Find function definition
        tree = ast.parse(source)
        func_def = find_function_def(tree, func_name)

        # Extract signature
        params = [p.arg for p in func_def.args.args]

        # Provide explicit guidance
        return f"""
        The function {func_name} has signature: ({', '.join(params)})
        You are missing the first parameter: {params[0]}
        You need to create a {params[0]} instance first.
        """
```

### 6. Add Retry Logic with Different Strategies (LOW)

**When stuck, try alternative approaches**:

Attempt 1-2: Direct approach
Attempt 3-4: Try mocking dependencies
Attempt 5-6: Try using fixtures from test_patch
Attempt 7+: Try minimal reproduction

---

## Priority Actions

### 🔴 IMMEDIATE (Do Today)
1. ✅ Switch to using `orchestrator.py` in `.sbatch` scripts
2. ✅ Fix guardrail probe logic for instance methods
3. ✅ Add explicit instance method handling instructions to prompts

### 🟡 HIGH (Do This Week)
4. Add source code reading capability when stuck
5. Enhance signature hints with instantiation examples
6. Add unit tests for guardrail probe logic

### 🟢 MEDIUM (Do This Sprint)
7. Implement retry with different strategies
8. Add more comprehensive examples to prompts
9. Create debugging mode that explains each step

---

## Testing the Fixes

### Test Case 1: pylint-dev__pylint-6506
**Expected after fix**:
- Agent reads that `_config_initialization` needs `linter` parameter
- Agent imports `PyLinter` and creates instance
- Test passes or fails for correct reason (not signature error)

### Test Case 2: psf__requests-2148
**Expected after fix**:
- Guardrail probe correctly skips `iter_content` (instance method)
- Test generation proceeds
- Agent creates Response instance with mocked raw stream
- Test properly checks exception handling

---

## Metrics to Track

1. **Early stopping rate**: % of instances that trigger stuck-in-loop detection
2. **Guardrail pass rate**: % that pass probe_check on first attempt
3. **Signature error rate**: % of failures due to signature mismatch
4. **Iteration efficiency**: Average iterations before success/failure
5. **Cost savings**: Compute hours saved by early stopping

---

## Additional Notes

- The grounding information IS being extracted correctly
- The issue is NOT lack of data but lack of **understanding/using** that data
- The LLM needs better guidance on:
  - Reading signatures
  - Understanding instance vs static methods
  - Creating required objects
  - Learning from feedback

- Consider using a code-focused model like DeepSeek Coder or CodeLlama for test generation
- Consider using few-shot examples showing correct instance method handling
