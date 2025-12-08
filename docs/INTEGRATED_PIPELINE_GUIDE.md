# 🔧 Modular Integrated Pipeline - Usage Guide

## Overview

The new **integrated_pipeline_modular.ipynb** combines three verification modules into one configurable pipeline:

1. **Static Analysis** - Code quality (Pylint, Flake8, Radon, Mypy, Bandit)
2. **Dynamic Fuzzing** - Change-aware property-based testing with real coverage
3. **Supplementary Rules** - 9 focused verification rules for targeted bug detection

## Key Benefits

### 🎛️ Modular Design
- **Enable/disable any module** via simple configuration
- Run only what you need (fast static checks vs. comprehensive verification)
- Independent thresholds for each module

### 🔍 Comprehensive Verification
- **Static** catches syntax/quality issues
- **Fuzzing** ensures coverage and test generation
- **Rules** detect semantic bugs (boundaries, state, concurrency, etc.)

### 📊 Ready for Streamlit
- Clear separation of concerns
- Configuration-driven execution
- Structured results output
- Easy to adapt to web interface

---

## Quick Start

### 1. Open the Notebook

```bash
cd /home/user/verifier_harness
jupyter notebook integrated_pipeline_modular.ipynb
```

### 2. Configure Modules

Edit the **Configuration** cell:

```python
ANALYSIS_CONFIG = {
    # Enable/disable analysis modules
    'enable_static': True,      # Static code quality
    'enable_fuzzing': True,     # Dynamic fuzzing
    'enable_rules': True,       # Verification rules

    # Thresholds
    'static_threshold': 0.5,
    'coverage_threshold': 0.5,
    'rules_fail_on_high_severity': True,

    # Display
    'show_detailed_results': True,
    'show_rule_findings': True,
    'show_uncovered_lines': True,
}
```

### 3. Run All Cells

Click **Cell → Run All** or run cells sequentially.

---

## Configuration Options

### Module Toggles

| Option | Description | Default |
|--------|-------------|---------|
| `enable_static` | Run static code quality analysis | `True` |
| `enable_fuzzing` | Run dynamic fuzzing with coverage | `True` |
| `enable_rules` | Run supplementary verification rules | `True` |

### Thresholds

| Option | Description | Default |
|--------|-------------|---------|
| `static_threshold` | Minimum SQI score (0-1) | `0.5` |
| `coverage_threshold` | Minimum coverage of changed lines (0-1) | `0.5` |
| `rules_fail_on_high_severity` | Reject patches with high-severity findings | `True` |

### Display Options

| Option | Description | Default |
|--------|-------------|---------|
| `show_detailed_results` | Show tool-by-tool breakdown | `True` |
| `show_rule_findings` | Show rule findings with severity | `True` |
| `show_uncovered_lines` | List uncovered line numbers | `True` |

---

## Usage Scenarios

### Scenario 1: Quick Static Check Only

```python
ANALYSIS_CONFIG = {
    'enable_static': True,
    'enable_fuzzing': False,
    'enable_rules': False,
}
```

**Use when:**
- Rapid feedback needed
- Pre-commit checks
- First-pass filtering

**Time:** ~30 seconds

---

### Scenario 2: Coverage Validation

```python
ANALYSIS_CONFIG = {
    'enable_static': False,
    'enable_fuzzing': True,
    'enable_rules': False,
}
```

**Use when:**
- Verifying test coverage
- Checking if changes are tested
- Fuzzing test generation

**Time:** ~2-5 minutes

---

### Scenario 3: Deep Semantic Verification

```python
ANALYSIS_CONFIG = {
    'enable_static': False,
    'enable_fuzzing': False,
    'enable_rules': True,
}
```

**Use when:**
- Looking for specific bug patterns
- Boundary/state/concurrency issues
- Post-fuzzing validation

**Time:** ~30-60 seconds

---

### Scenario 4: Full Verification (Default)

```python
ANALYSIS_CONFIG = {
    'enable_static': True,
    'enable_fuzzing': True,
    'enable_rules': True,
}
```

**Use when:**
- Final patch approval
- Critical code paths
- Production deployments

**Time:** ~3-6 minutes

---

## Understanding Results

### Verdict Categories

| Verdict | Meaning | Action |
|---------|---------|--------|
| ✅ **EXCELLENT** | Score ≥80%, all checks passed | Accept |
| ✓ **GOOD** | Score ≥60%, all checks passed | Accept |
| ⚠️ **WARNING** | Some non-critical issues | Review |
| ⚠️ **FAIR** | Low score but passed | Review |
| ❌ **REJECT** | Critical failures | Reject |

### Module Results

#### Static Analysis
```
Static Analysis: 61.5/100 ✅
```
- Shows SQI (Static Quality Index)
- ✅ = passed threshold
- ❌ = below threshold (< 50 by default)

#### Fuzzing
```
Fuzzing Tests: PASS ✅ (1 generated)
Coverage: 20.0% ⚠️
```
- Shows if generated tests passed
- Coverage of **changed lines only**
- ⚠️ = below threshold

#### Rules
```
Verification Rules: 8/9 passed ✅
  ⚠️  1 high-severity finding(s)
```
- Shows passed/failed rule count
- Lists severity of findings
- High-severity can trigger rejection

---

## Supplementary Rules Explained

The 9 verification rules target specific bug patterns:

### Rule 1: Boundary and Intersection Probing
- **Detects:** Off-by-one errors, boundary shifts
- **Example:** `if retries > 3:` changed to `>=`

### Rule 2: Predicate Influence (MC/DC)
- **Detects:** Masked boolean logic, ineffective clauses
- **Example:** `if admin or (owner and not suspended):` still blocks suspended admins

### Rule 3: State Transition Tours
- **Detects:** Incorrect state progressions
- **Example:** Returns before setting `conn.state = CLOSED`

### Rule 4: Definition-Use Execution
- **Detects:** Use-before-def, missing cleanup
- **Example:** Cache built conditionally but used unconditionally

### Rule 5: Resource Lifecycle Under Load
- **Detects:** Memory leaks, file descriptor exhaustion
- **Example:** Forgot `resp.close()` in retry loop

### Rule 6: Robust Exception Paths
- **Detects:** Incorrect exception handling, wrong status codes
- **Example:** `FileNotFoundError` → generic `Exception`, returns 500 instead of 404

### Rule 7: Transaction Order & Parameters
- **Detects:** API misuse, parameter ordering errors
- **Example:** `connect(host, *, ssl=True)` called as `connect(True, host)`

### Rule 8: Structured Input Validation
- **Detects:** Schema mismatches, type errors
- **Example:** Field renamed `id` → `user_id`, payload breaks

### Rule 9: Concurrency & Interlocks
- **Detects:** Deadlocks, race conditions
- **Example:** Unlock moved after return, concurrent calls deadlock

---

## Output Files

### Results JSON
```json
{
  "instance_id": "scikit-learn__scikit-learn-10297",
  "overall_score": 75.5,
  "verdict": "✓ GOOD",
  "enabled_modules": {
    "static": true,
    "fuzzing": true,
    "rules": true
  },
  "static": {
    "sqi_score": 61.5,
    "passed": true
  },
  "fuzzing": {
    "combined_coverage": 20.0,
    "tests_generated": 1,
    "passed": false
  },
  "rules": {
    "total_rules": 9,
    "failed_rules": 1,
    "high_severity_count": 1,
    "passed": false
  }
}
```

Saved to: `integrated_pipeline_results.json`

### Visualization
- Bar charts for each module
- Coverage pie chart
- Rules pass/fail counts

Saved to: `integrated_pipeline_viz.png`

---

## Comparison: Old vs New Pipeline

### Old: fuzzing_pipeline_real_coverage.ipynb
- **Modules:** Static + Fuzzing
- **Configuration:** Hard-coded
- **Coverage:** Line-by-line (real)
- **Rules:** None

### New: integrated_pipeline_modular.ipynb
- **Modules:** Static + Fuzzing + **Rules** ✨
- **Configuration:** Flexible, module-based
- **Coverage:** Line + branch (real)
- **Rules:** 9 semantic verification rules ✨

### What's New?
1. **Supplementary Rules** - Catch semantic bugs fuzzing misses
2. **Modular Config** - Enable/disable any module
3. **Severity Levels** - High/medium/low rule findings
4. **Better Verdicts** - Combined scoring from all modules
5. **Streamlit-Ready** - Clean separation for web UI

---

## Integration with evaluation_pipeline.py

The notebook uses the same underlying `EvaluationPipeline` class:

```python
from evaluation_pipeline import EvaluationPipeline

pipeline = EvaluationPipeline(
    enable_static=True,
    enable_fuzzing=True,
    enable_rules=True,
    static_threshold=0.5,
    coverage_threshold=0.5,
    rules_fail_on_high_severity=True,
)

result = pipeline.evaluate_patch({
    'id': instance_id,
    'diff': patch_str,
    'repo_path': repo_path,
})
```

This makes it easy to:
- Use programmatically in scripts
- Integrate into CI/CD
- Build web interfaces (Streamlit)

---

## Next Steps: Streamlit Integration

The modular design is ready for Streamlit:

### Streamlit UI Structure

```python
# Sidebar: Module selection
st.sidebar.header("Analysis Modules")
enable_static = st.sidebar.checkbox("Static Analysis", value=True)
enable_fuzzing = st.sidebar.checkbox("Dynamic Fuzzing", value=True)
enable_rules = st.sidebar.checkbox("Verification Rules", value=True)

# Main area: Results
if st.button("Run Analysis"):
    pipeline = EvaluationPipeline(
        enable_static=enable_static,
        enable_fuzzing=enable_fuzzing,
        enable_rules=enable_rules,
    )

    result = pipeline.evaluate_patch(patch_data)

    # Display results
    st.metric("Overall Score", f"{result['overall_score']:.1f}/100")
    st.header(result['verdict'])

    # Tabs for each module
    tab1, tab2, tab3 = st.tabs(["Static", "Fuzzing", "Rules"])

    with tab1:
        # Static results...
    with tab2:
        # Fuzzing results...
    with tab3:
        # Rules results...
```

### Key Advantages for Streamlit
1. **Single config dict** → Easy to map to UI controls
2. **Structured results** → Easy to render in tabs/sections
3. **Independent modules** → Can show/hide based on selection
4. **JSON output** → Easy to cache and display

---

## Troubleshooting

### Issue: Rules showing "No repo path"
**Solution:** Ensure `repo_path` is set before running rules module.

### Issue: Coverage is 0% but tests pass
**Solution:** Check `coverage_source` matches the module being tested (e.g., `sklearn`).

### Issue: High-severity rule findings seem wrong
**Solution:** Check rule details in `result['rules']['details']` for context.

### Issue: Notebook too slow
**Solution:** Disable modules you don't need:
```python
ANALYSIS_CONFIG = {
    'enable_static': True,   # Fast (30s)
    'enable_fuzzing': False, # Slow (3-5min)
    'enable_rules': True,    # Fast (30s)
}
```

---

## Summary

The **integrated_pipeline_modular.ipynb** provides:

✅ **Flexibility** - Enable only what you need
✅ **Comprehensiveness** - Static + Fuzzing + Rules
✅ **Clarity** - Clear module separation and results
✅ **Actionability** - Detailed findings with locations
✅ **Extensibility** - Ready for Streamlit/web UI

**Use it when you need configurable, comprehensive patch verification!**
