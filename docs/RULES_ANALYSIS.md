# Analysis: Rules Directory & Integration with Fuzzing Pipeline

## Executive Summary

Your colleague has implemented a **comprehensive supplementary verification rule system** consisting of 9 specialized rules that target specific bug taxonomy classes (from `papers/bug_taxonomy.pdf`). These rules fill critical gaps left by existing static analyzers and coverage-based fuzzing by using focused testing techniques from systematic test theory.

**Key Finding:** The rules system is **highly complementary** to your `fuzzing_pipeline_real_coverage` and should be integrated as an additional verification layer.

---

## What is the Rules Directory?

### Structure
```
verifier/rules/
├── base.py              # Core types: RuleResult, RuleImplementation
├── helpers.py           # Utilities: parse patches, load modules, gather changed functions
├── runner.py            # CLI/API runner for executing rules
├── rule_1/ to rule_9/   # Individual rule implementations
│   ├── rule.py          # Main implementation
│   └── EXPLANATION.md   # Documentation
└── __init__.py          # Package exports

tests/rules/             # Test suite for rules
├── test_rule_1_boundary_and_intersections.py
├── test_rule_2_predicate_influence.py
└── ... (9 total)
```

### Core Concept

Each rule:
1. **Takes as input**: Repository path + unified diff patch
2. **Analyzes**: Specific bug patterns from the taxonomy
3. **Returns**: Structured `RuleResult` with:
   - Status: `passed` | `failed` | `skipped`
   - Findings: List of discovered issues with location, severity, taxonomy tags
   - Metrics: Quantitative measurements (functions checked, probes run, etc.)

---

## The 9 Rules: What They Do

### **Rule 1: Boundary and Intersection Probing**
- **Targets**: Taxonomy 241x-244x (boundary errors)
- **Technique**: Detects operator shifts (`>=` → `>`) and constant changes (±1), then executes boundary probes (threshold-1, threshold, threshold+1)
- **Example Bug**: Changed `if retries > 3:` to `>=` wrongly rejects exactly 3 attempts
- **Value**: Catches off-by-one errors that tests miss

### **Rule 2: Predicate Influence (MC/DC-Style)**
- **Targets**: Taxonomy 312x (control predicates), 244x (intersections)
- **Technique**: Builds MC/DC decision tables for boolean expressions to ensure each condition independently affects outcomes
- **Example Bug**: `if is_admin or (is_owner and not suspended):` still blocks suspended admins
- **Value**: Detects masked or duplicated logic

### **Rule 3: State Transition Tours**
- **Targets**: Taxonomy 3154 (state transitions), 316x (exception flow)
- **Technique**: Models state machines from patches and verifies each transition plus two-step tours
- **Example Bug**: Error branch returns before setting `conn.state = CLOSED`
- **Value**: Catches incorrect multi-step state progressions

### **Rule 4: Definition–Use Execution**
- **Targets**: Taxonomy 323x (initialization), 324x (cleanup), 428x (access anomalies)
- **Technique**: Enumerates def-use chains for changed variables and forces execution of each path
- **Example Bug**: Cache built only when flag enabled but used unguarded later
- **Value**: Detects use-before-def and missing cleanup

### **Rule 5: Resource Lifecycle Under Load**
- **Targets**: Taxonomy 416x (resource mis-specification), 426x (runtime resource handling)
- **Technique**: Loops operations 50-200 times, monitors file descriptors/handles with `psutil`
- **Example Bug**: Retry loop forgets `resp.close()` inside loop
- **Value**: Exposes leaks/exhaustion only visible after repetition

### **Rule 6: Robust Exception and Message Paths**
- **Targets**: Taxonomy 26xx (exception mishandling), 25xx (user messages)
- **Technique**: Forces dependency failures and malformed inputs, verifies exception types and messages
- **Example Bug**: Patch collapses `FileNotFoundError` to generic `Exception`, returns 500 instead of 404
- **Value**: Ensures proper error handling and diagnostics

### **Rule 7: Transaction Order and Parameter Contracts**
- **Targets**: Taxonomy 611x-612x (invocation/parameter errors), 622x (return misinterpretation)
- **Technique**: Validates call sequences (init → use → teardown) and parameter ordering
- **Example Bug**: `connect(host, *, ssl=True)` called as `connect(True, host)` disables TLS
- **Value**: Catches API misuse and contract violations

### **Rule 8: Structured Input and Conversion Validation**
- **Targets**: Taxonomy 4214 (type transformation), 422x (dimensions), 4285 (object access)
- **Technique**: Treats inputs as grammar, tests valid/near-miss/malformed variants
- **Example Bug**: Field renamed `id` → `user_id`; payload `{ "id": 1 }` becomes `None`
- **Value**: Detects schema mismatches and bounds violations

### **Rule 9: Concurrency and Interlock Order Checks**
- **Targets**: Taxonomy 721x (interlocks/semaphores), 742x (timing sensitivity)
- **Technique**: Stresses patches with concurrent workers and randomized scheduling
- **Example Bug**: Unlock moved after return; concurrent calls deadlock
- **Value**: Exposes races and deadlocks

---

## How Rules Work (Implementation)

### Example: Rule 1 Flow

1. **Parse Patch**:
   ```python
   patch_data = parse_patch_by_file(patch_str)
   # {'file.py': {'added': [...], 'removed': [...]}}
   ```

2. **Detect Pattern**:
   ```python
   operator_findings = _detect_operator_shifts(patch_data)
   # Finds: 'Boundary changed from >= to >: ...'
   ```

3. **Extract Functions**:
   ```python
   changed_functions = gather_changed_functions(repo_path, patch_str)
   # Loads actual Python functions from patched code
   ```

4. **Execute Probes**:
   ```python
   thresholds = _extract_thresholds(func_info.func)  # [3.0]
   runs, collapsed = _probe_boundaries(func_info, thresholds)
   # Calls func(2), func(3), func(4) and checks for distinct outcomes
   ```

5. **Report Findings**:
   ```python
   result.add_finding(
       "Boundary inputs collapse to same outcome",
       location="file.py:42",
       taxonomy_tags=["boundary", "intersection"]
   )
   ```

### Running Rules

**CLI:**
```bash
# Run all rules
python -m verifier.rules.runner --rule all --repo /path/to/repo --patch-file patch.diff

# Run specific rule
python -m verifier.rules.runner --rule rule_1 --repo /path/to/repo --patch-stdin < patch.diff
```

**Programmatic:**
```python
from verifier.rules.runner import run_rules

results = run_rules(
    rule_ids=["rule_1", "rule_2"],
    repo_path="/path/to/repo",
    patch_str=diff_content
)

for result in results:
    print(f"{result.name}: {result.status}")
    for finding in result.findings:
        print(f"  - {finding['description']} at {finding['location']}")
```

---

## Comparison: Rules vs. Fuzzing Pipeline

### Current Fuzzing Pipeline (`fuzzing_pipeline_real_coverage`)

**What it does:**
- Analyzes patches to find changed functions/lines
- Generates property-based tests using Hypothesis
- Runs tests in Singularity container with coverage collection
- Measures line-by-line coverage of changed code
- Reports: "60% of changed lines covered, lines [42, 45, 47] untested"

**Strengths:**
- ✅ Real execution coverage (not proxy)
- ✅ Generates tests automatically
- ✅ Container isolation
- ✅ Change-aware (focuses on modified code)
- ✅ Actionable output (exact line numbers)

**Gaps:**
- ❌ Coverage ≠ correctness (line executed doesn't mean behavior is correct)
- ❌ Generated tests may be shallow (e.g., `assert hasattr(Class, 'method')`)
- ❌ Doesn't target specific bug patterns
- ❌ No semantic validation (boundary correctness, state transitions, etc.)

### Rules System

**What it does:**
- Targets specific bug taxonomy classes
- Uses focused testing techniques (MC/DC, state tours, def-use, etc.)
- Executes semantic checks (boundary probing, predicate influence, etc.)
- Reports: "Boundary at line 42 collapses all inputs to same outcome"

**Strengths:**
- ✅ Semantic validation (checks correctness, not just execution)
- ✅ Targets known bug patterns from research
- ✅ Lightweight (no heavy fuzzing infrastructure)
- ✅ Specific findings with taxonomy tags
- ✅ Fast (focused probes, not exhaustive testing)

**Gaps:**
- ❌ Limited to changed functions (no full codebase analysis)
- ❌ Simple probes (may miss complex bugs)
- ❌ No test generation (only verification)
- ❌ Requires loadable Python modules

---

## Integration Recommendations

### Option 1: Parallel Verification Layer (Recommended)

Add rules as a **third phase** after static analysis and fuzzing:

```python
# In evaluation_pipeline.py

def evaluate_patch(self, patch_data):
    # PHASE 1: Static Verification
    static_result = self._run_static_verification(patch_data)

    # PHASE 2: Dynamic Fuzzing
    fuzzing_result = self._run_dynamic_fuzzing(patch_data)

    # PHASE 3: Supplementary Rules (NEW!)
    rules_result = self._run_supplementary_rules(patch_data)

    # FINAL VERDICT: Consider all three
    verdict = self._compute_final_verdict(
        static_result,
        fuzzing_result,
        rules_result
    )
```

**Benefits:**
- Rules catch semantic bugs fuzzing misses
- Fuzzing provides coverage guarantees
- Static analysis catches syntax/quality issues
- Comprehensive defense-in-depth

**Implementation:**
```python
def _run_supplementary_rules(self, patch_data: Dict) -> Dict:
    """Run focused verification rules"""
    from verifier.rules.runner import run_rules
    from verifier.rules import RULE_IDS

    repo_path = patch_data.get('repo_path')
    diff = patch_data.get('diff', '')

    if not repo_path:
        return {'status': 'skipped', 'reason': 'No repo path'}

    try:
        # Run all rules
        results = run_rules(
            rule_ids=RULE_IDS,
            repo_path=str(repo_path),
            patch_str=diff
        )

        # Aggregate findings
        all_findings = []
        failed_rules = []

        for result in results:
            if result.status == 'failed':
                failed_rules.append(result.name)
                all_findings.extend(result.findings)

        return {
            'status': 'completed',
            'total_rules': len(results),
            'failed_rules': len(failed_rules),
            'rule_names': failed_rules,
            'findings': all_findings,
            'details': [r.to_dict() for r in results]
        }

    except Exception as e:
        return {'status': 'error', 'error': str(e)}
```

**Verdict Logic:**
```python
def _compute_final_verdict(self, static, fuzzing, rules):
    # Hard failures
    if static['sqi_score'] < 0.5:
        return 'REJECT', 'Poor static quality'

    if not fuzzing.get('tests_passed', False):
        return 'REJECT', 'Fuzzing tests failed'

    if rules['failed_rules'] > 0:
        severity_high = any(
            f['severity'] == 'high'
            for f in rules['findings']
        )
        if severity_high:
            return 'REJECT', f"Critical bugs found: {rules['rule_names']}"
        else:
            return 'WARNING', f"Potential bugs found: {rules['rule_names']}"

    # Soft warnings
    if fuzzing['coverage']['overall_coverage'] < 0.6:
        return 'WARNING', 'Low coverage'

    return 'ACCEPT', 'All checks passed'
```

### Option 2: Coverage-Guided Rule Selection

Only run rules relevant to uncovered lines:

```python
# After fuzzing, check what's uncovered
uncovered_lines = fuzzing_result['coverage']['uncovered_lines']

# Map lines to relevant rules
relevant_rules = []
if has_boundary_changes(diff):
    relevant_rules.append('rule_1')
if has_boolean_logic(diff):
    relevant_rules.append('rule_2')
# ... etc

# Run only relevant rules
results = run_rules(relevant_rules, repo_path, diff)
```

**Benefits:**
- Faster (only runs needed rules)
- Focuses on gaps fuzzing didn't cover

**Drawbacks:**
- More complex logic
- May miss cross-cutting bugs

### Option 3: Rule-Guided Test Generation

Use rule findings to improve fuzzing:

```python
# Run rules first
rules_result = run_rules(RULE_IDS, repo_path, diff)

# Extract hints for test generation
for finding in rules_result.findings:
    if 'boundary' in finding['taxonomy_tags']:
        # Generate tests targeting that boundary
        test_code += generate_boundary_tests(finding)
    elif 'state' in finding['taxonomy_tags']:
        # Generate state transition tests
        test_code += generate_state_tests(finding)

# Run enhanced fuzzing
fuzzing_result = run_tests(test_code)
```

**Benefits:**
- Rules guide fuzzing to problem areas
- Best of both worlds

**Drawbacks:**
- Requires new test generation logic
- More complex integration

---

## Recommendation Summary

### **Immediate Action: Add Rules as Phase 3**

1. **Add to `evaluation_pipeline.py`**:
   ```python
   # After fuzzing phase
   if self.enable_rules:
       rules_result = self._run_supplementary_rules(patch_data)
       result['rules_result'] = rules_result
   ```

2. **Update verdict logic** to consider rule failures as blockers for high-severity findings

3. **Test on existing patches** to calibrate severity thresholds

### **Why This is Valuable**

The rules system provides **semantic validation** that coverage-based fuzzing cannot:

- **Fuzzing says**: "Line 42 was executed"
- **Rules say**: "Line 42's boundary logic is incorrect"

Example scenario:
```python
# Patch changes:
- if retries >= 3:
+ if retries > 3:

# Fuzzing result: 100% coverage (line executed)
# Rule 1 result: FAILED - boundary shifted, retries=3 case missing

# Without rules: Patch accepted (all lines covered)
# With rules: Patch rejected (semantic bug detected)
```

---

## Quick Start Guide

### 1. Test Rules Standalone
```bash
cd /home/user/verifier_harness

# Run all rules on a test patch
python -m verifier.rules.runner \
    --rule all \
    --repo ./tests/rules/r1 \
    --patch-file ./tests/rules/r1/patch.diff

# Run rule tests
pytest tests/rules/ -v
```

### 2. Integrate into Fuzzing Pipeline
```python
# Add to fuzzing_pipeline_real_coverage.ipynb

from verifier.rules.runner import run_rules
from verifier.rules import RULE_IDS

# After Stage 10 (coverage analysis)
print("\n[Stage 11] Running Supplementary Rules...")

rules_results = run_rules(
    rule_ids=RULE_IDS,
    repo_path=repo_path,
    patch_str=patch_diff
)

# Check for critical findings
critical_findings = []
for result in rules_results:
    if result.status == 'failed':
        print(f"  ⚠️  {result.name}: {len(result.findings)} findings")
        for finding in result.findings:
            if finding['severity'] == 'high':
                critical_findings.append(finding)
                print(f"    - {finding['description']} at {finding['location']}")

if critical_findings:
    print(f"\n❌ VERDICT: REJECT ({len(critical_findings)} critical bugs found)")
else:
    print(f"\n✅ VERDICT: Rules passed")
```

### 3. Monitor Results
Track metrics:
- Rules triggered per patch
- Most common findings
- False positive rate
- Correlation with actual bugs

---

## Conclusion

**The rules directory is a valuable semantic verification layer** that complements your fuzzing pipeline:

| Aspect | Fuzzing Pipeline | Rules System | Combined |
|--------|-----------------|--------------|----------|
| Coverage | ✅ Line-by-line | ❌ No | ✅ Complete |
| Correctness | ⚠️ Shallow | ✅ Semantic | ✅ Deep |
| Bug Targeting | ❌ General | ✅ Taxonomy | ✅ Focused |
| Test Generation | ✅ Automatic | ❌ No | ✅ Automatic |
| Speed | ⚠️ Moderate | ✅ Fast | ⚠️ Moderate |

**Recommendation**: Integrate rules as a supplementary phase in your evaluation pipeline to achieve comprehensive coverage + semantic validation.
