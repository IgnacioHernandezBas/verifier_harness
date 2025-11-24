# 🚀 Quick Start: Real Coverage Measurement

**TL;DR:** We replaced fake coverage (0/50/100%) with real line-by-line coverage tracking.

---

## ⚡ Run This Now

```bash
# 1. Verify the infrastructure works
python test_real_coverage.py

# Expected output:
# ✅ ALL TESTS PASSED!
# 🎉 Real coverage measurement is working correctly!
```

---

## 🎯 What Changed (Visual)

### **OLD: Coverage Proxy (Fake)**
```
┌─────────────────────────────────────┐
│  Existing Tests: PASS  → 50%        │
│  Fuzzing Tests:  PASS  → +50%       │
│                                      │
│  Coverage: 100% ✅                   │
│                                      │
│  Problem: No idea what was tested!  │
└─────────────────────────────────────┘
```

### **NEW: Real Coverage (Precise)**
```
┌──────────────────────────────────────────────────┐
│  Changed Lines: [3, 4, 5, 7, 8, 9, 10]  (7 total) │
│  Tested Lines:  [3, 5, 7, 10]           (4 tested)│
│  Untested:      [4, 8, 9]               (3 missed)│
│                                                   │
│  Coverage: 57.1% ⚠️                               │
│                                                   │
│  Action: Generate tests for lines 4, 8, 9!       │
└──────────────────────────────────────────────────┘
```

---

## 📂 Files You Need to Know

| **File** | **Purpose** | **Action** |
|----------|-------------|------------|
| `fuzzing_pipeline_real_coverage.ipynb` | **USE THIS** for new runs | Open in Jupyter, run all cells |
| `test_real_coverage.py` | Test the infrastructure | `python test_real_coverage.py` |
| `REAL_COVERAGE_UPGRADE.md` | Full documentation | Read for details |
| `verifier/dynamic_analyzers/test_patch_singularity.py` | Modified to collect coverage | Already updated ✅ |

---

## 🎓 Before vs After Example

### **Scenario: LLM adds error handling**

```python
# Patch adds these lines:
+   if value is None:        # Line 42
+       raise ValueError()   # Line 43
    return process(value)    # Line 44 (unchanged)
```

### **Old System Output:**
```
Coverage proxy: 100%
Verdict: EXCELLENT ✅
```
☠️ **Problem:** Lines 42-43 were NEVER tested, but we reported 100% coverage!

### **New System Output:**
```
Changed Lines: 2
Covered Lines: 0 (0%)
Uncovered Lines: [42, 43]

⚠️ WARNING: Error handling on lines 42-43 NOT TESTED!

Verdict: POOR (Low coverage)
```
✅ **Solution:** We know exactly what to test!

---

## 🔧 How to Use in 3 Steps

### **Step 1: Run tests with coverage**
```python
result = run_tests_in_singularity(
    repo_path=Path("./repo"),
    tests=["test_foo.py"],
    image_path="container.sif",
    collect_coverage=True,        # 🔥 NEW!
    coverage_source="sklearn",    # 🔥 NEW!
)
```

### **Step 2: Analyze coverage**
```python
from verifier.dynamic_analyzers.coverage_analyzer import CoverageAnalyzer

coverage_data = json.loads(Path(result['coverage_file']).read_text())
analyzer = CoverageAnalyzer()

coverage_result = analyzer.calculate_changed_line_coverage(
    coverage_data=coverage_data,
    changed_lines=patch_analysis.changed_lines,
    all_changed_lines=patch_analysis.all_changed_lines
)
```

### **Step 3: Check uncovered lines**
```python
print(f"Coverage: {coverage_result['overall_coverage']*100:.1f}%")
print(f"Uncovered: {coverage_result['uncovered_lines']}")

# Example output:
# Coverage: 63.2%
# Uncovered: [42, 43, 67, 89]
```

---

## 🎯 What You Get

### **Precise Metrics:**
- Overall coverage: `63.2%` (not just 0/50/100%)
- Per-function: `divide: 100%, multiply: 33%`
- Exact uncovered lines: `[4, 8, 9, 15]`

### **Actionable Reports:**
```
================================================================================
CHANGE-AWARE COVERAGE REPORT
================================================================================

Changed Functions: divide, multiply
Total Changed Lines: 12
Covered Changed Lines: 8
Overall Coverage: 66.7%

Per-Function Coverage:
  ✓ divide: 100.0%
  ⚠ multiply: 33.3%

Uncovered Lines (4):
  [8, 9, 15, 23]

================================================================================
```

### **Better Verdicts:**
```
Verdict: ⚠️ FAIR (⚠️ Moderate coverage)

Component Scores:
  Static Analysis: 61.5/100
  Existing Tests: PASS (29 tests)
  Fuzzing Tests: PASS (1 test)
  Change-Aware Coverage: 66.7% (8/12 lines) 🔥

⚠️ WARNING: 4 changed lines remain UNTESTED
   Line numbers: [8, 9, 15, 23]
```

---

## 🐛 Common Issues

### **"No coverage file generated"**
**Cause:** Tests failed (pytest-cov uses `--no-cov-on-fail`)
**Solution:** Fix failing tests first

### **"Coverage is 0% but tests pass"**
**Cause:** Wrong `coverage_source` module
**Solution:**
```python
# Get module from patch analysis
module = patch_analysis.module_path.split('.')[0]  # e.g., "sklearn"
coverage_source = module
```

### **"Coverage file exists but empty"**
**Cause:** Coverage source doesn't match actual module structure
**Solution:** Check the actual Python package name

---

## 📊 Expected Coverage Ranges

Based on patch types:

| **Patch Type** | **Expected Coverage** | **Reason** |
|----------------|----------------------|-----------|
| Bug fix (small) | 60-90% | Usually well-tested paths |
| New feature | 30-60% | Many edge cases uncovered |
| Refactoring | 70-95% | Existing tests cover most paths |
| Error handling | 20-50% | Hard to trigger all error paths |
| Class methods | 10-40% | Fuzzing struggles with constructors |

---

## 🎯 Success Checklist

- [x] `test_real_coverage.py` passes
- [ ] Run `fuzzing_pipeline_real_coverage.ipynb` on scikit-learn patch
- [ ] Coverage shows precise % (not just 0/50/100)
- [ ] Uncovered lines are listed
- [ ] Per-function breakdown appears
- [ ] Verdict includes coverage warning if low

---

## 🚀 Next: Run on Real Patch

```bash
# Open the new notebook
jupyter notebook fuzzing_pipeline_real_coverage.ipynb

# Run all cells
# Compare with old notebook results
# Check that uncovered lines are identified
```

**Expected timeline:**
- ⏱️ 5-10 minutes for full pipeline
- 📊 Real coverage data appears in Stage 10
- 🎯 Actionable uncovered lines in final verdict

---

## 💡 Pro Tips

1. **Save the coverage JSON:** Useful for debugging and comparison
   ```python
   coverage_file = Path(result['coverage_file'])
   coverage_file.rename('coverage_scikit_10297.json')  # Keep for later
   ```

2. **Compare before/after:** Run old notebook then new notebook
   ```python
   # Old: coverage_proxy = 100%
   # New: actual_coverage = 63.2%
   # Difference: 36.8% of code was NOT tested!
   ```

3. **Focus on uncovered lines:** These are your testing gaps
   ```python
   if coverage_result['uncovered_lines']:
       print("🎯 Generate tests for these lines:")
       for line in coverage_result['uncovered_lines']:
           print(f"   Line {line}: {get_code_at_line(line)}")
   ```

4. **Track coverage over time:**
   ```python
   # Save results to database/CSV
   results = {
       'patch_id': instance_id,
       'coverage': coverage_result['overall_coverage'],
       'uncovered_lines': coverage_result['uncovered_lines'],
       'timestamp': time.time()
   }
   ```

---

## 🎉 You're Ready!

The engine is swapped. Your verification harness now has:
- ✅ Real line-by-line coverage tracking
- ✅ Precise metrics (not binary pass/fail)
- ✅ Actionable uncovered line identification
- ✅ Per-function coverage breakdown

**Go ahead and run that notebook! 🚀**
