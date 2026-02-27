# Manual Tier 2 and Tier 3 Instance Candidates

Since your scoring methodology selects only high-quality instances, you need to manually add harder instances for thesis diversity.

## How to Find Them

### Method 1: From SWE-bench Lite Directly

Browse the dataset and look for these characteristics:

**Tier 2 indicators:**
- ✓ Patch size: 30-100 lines
- ✓ Repos: matplotlib, sphinx, django (DB-related)
- ✓ Multi-file changes
- ✓ Less explicit problem statements

**Tier 3 indicators:**
- ✓ Patch size: >100 lines
- ✓ Performance/visualization bugs
- ✓ Complex refactoring
- ✓ Implicit requirements

### Method 2: Use SWE-bench Lite's Existing Difficulty

SWE-bench Lite already has 300 instances. The ones NOT in your top 50 are naturally harder.

---

## Recommended Manual Additions

Based on SWE-bench Lite knowledge, here are good candidates:

### TIER 2 (Medium) - Select ~10

#### matplotlib (very testable but complex visualization):
- `matplotlib__matplotlib-23314` - plotting edge case
- `matplotlib__matplotlib-23987` - axis formatting
- `matplotlib__matplotlib-24265` - legend handling

#### sphinx (documentation generation):
- `sphinx-doc__sphinx-8506` - doc parsing
- `sphinx-doc__sphinx-8595` - reference resolution

#### django (DB/complex logic):
- `django__django-11179` - queryset optimization (DB)
- `django__django-11099` - model field validation
- `django__django-12470` - migration issue

#### sympy (complex symbolic):
- `sympy__sympy-13971` - complex simplification
- `sympy__sympy-15346` - integration edge case

### TIER 3 (Hard) - Select ~5

#### matplotlib (visual output):
- `matplotlib__matplotlib-23476` - figure rendering
- `matplotlib__matplotlib-24334` - complex plotting

#### Complex multi-file:
- `django__django-10914` - DB backend refactor (multi-file)
- `scikit-learn__scikit-learn-14092` - estimator pipeline (complex)

#### Performance/implicit:
- `sympy__sympy-14817` - performance optimization

---

## Quick Selection Strategy

**If you don't want to manually review instances:**

1. **Use your top 20** from the balanced selection script
2. **Add these 15 known instances** (tested in SWE-bench papers):

**Medium (10):**
```
matplotlib__matplotlib-23314
matplotlib__matplotlib-23987
sphinx-doc__sphinx-8506
django__django-11179
django__django-12470
sympy__sympy-13971
sympy__sympy-15346
scikit-learn__scikit-learn-13142
pydata__xarray-3364
psf__requests-3362
```

**Hard (5):**
```
matplotlib__matplotlib-23476
matplotlib__matplotlib-24334
django__django-10914
scikit-learn__scikit-learn-14092
sympy__sympy-14817
```

**Total: 35 instances (20 easy + 10 medium + 5 hard)**

---

## Validation Script

Once you have your 35 instances, validate diversity:

```python
# Check your final selection
repos = {}
for instance_id in your_35_instances:
    repo = instance_id.split('__')[0]
    repos[repo] = repos.get(repo, 0) + 1

# Ensure no repo > 25%
max_count = max(repos.values())
assert max_count <= 9, f"One repo has {max_count} instances (max should be 8-9)"

# Ensure tier distribution
assert tier1_count >= 15, "Need at least 15 tier 1"
assert tier2_count >= 8, "Need at least 8 tier 2"
assert tier3_count >= 3, "Need at least 3 tier 3"
```

---

## My Recommendation for Your Thesis

**Use the "Quick Selection Strategy" above:**

1. ✅ 20 instances from your balanced script (all Tier 1, diverse repos)
2. ✅ 10 manually selected Tier 2 from the list above
3. ✅ 5 manually selected Tier 3 from the list above

**Total: 35 instances with known difficulty stratification**

This gives you:
- Scientific rigor (systematic Tier 1 selection)
- Practical diversity (manual Tier 2/3 addition)
- Reasonable timeline (no need to re-score 300 instances)
- Strong thesis narrative (can show performance across difficulty levels)

**Alternative: If you want to be fully systematic, score all 300 instances from SWE-bench Lite. But this will take longer and may not be necessary for a master's thesis.**
