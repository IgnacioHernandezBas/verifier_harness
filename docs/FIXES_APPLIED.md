# Fixes Applied - December 4, 2025

## Issue 1: Docker Image Naming Pattern for pytest Repositories

### Problem
Container builds were failing for pytest repositories with authentication errors:
```
FATAL: While performing build: conveyor failed to get: GET https://index.docker.io/v2/swebench/sweb.eval.x86_64.pytest_1776_pytest-5262/manifests/latest: UNAUTHORIZED
```

The image pattern was using `{repo}_1776_{repo}` which only works when organization name equals repository name (e.g., `scikit-learn__scikit-learn`). It failed for repos where they differ (e.g., `pytest-dev__pytest`).

### Root Cause
Docker Hub images use organization name in the pattern:
- ✅ Correct: `sweb.eval.x86_64.pytest-dev_1776_pytest-5262`
- ❌ Wrong: `sweb.eval.x86_64.pytest_1776_pytest-5262`

### Solution
Changed pattern from `{repo}_1776_{repo}` to `{org}_1776_{repo}` in:
- `scripts/slurm/slurm_worker_integrated.py` (line 56)
- `scripts/slurm/slurm_worker_analyze.py` (line 90)
- `scripts/slurm/slurm_worker_build.py` (line 33)

### Verification
All repos now resolve correctly:
- **pytest-dev__pytest-5262** → `pytest-dev_1776_pytest-5262` ✅
- **scikit-learn__scikit-learn-10297** → `scikit-learn_1776_scikit-learn-10297` ✅
- **django__django-10087** → `django_1776_django-10087` ✅

---

## Issue 2: Test Framework Detection (Django vs Pytest)

### Problem
Baseline tests were failing for Django and pytest repos:
- **sklearn**: 84.6% pass rate ✅
- **django**: 0% pass rate (RC:4 - command line usage error) ❌
- **pytest**: 0% pass rate (varies) ❌

Django tests were being run with pytest, which doesn't work because Django uses its own test runner with unittest-style test names.

### Root Cause
The code hardcoded `python -m pytest` for all test execution. Django test names have different format:
- **Pytest**: `testing/logging/test_fixture.py::test_clear_for_call_stage`
- **Django**: `test_ascii_validator (auth_tests.test_validators.UsernameValidatorsTests)`

### Solution
Added automatic test framework detection in `test_patch_singularity.py`:

1. **Framework Detection** (line 485-497):
   - If test contains `::` → pytest
   - If test contains `(` and `)` → Django
   - Default fallback → pytest

2. **Django Test Name Conversion** (line 499-511):
   - Input: `test_ascii_validator (auth_tests.test_validators.UsernameValidatorsTests)`
   - Output: `auth_tests.test_validators.UsernameValidatorsTests.test_ascii_validator`

3. **Framework-Specific Test Commands** (line 572-687):
   - **Django**: `python -m django test <converted_tests>`
   - **Django with coverage**: `python -m coverage run --source <src> --branch -m django test`
   - **Pytest**: `python -m pytest <tests>` (with optional --cov)

### Expected Impact
- Django tests should now run with proper test runner
- Django baseline tests should pass (if ground truth patches are correct)
- Pytest tests should continue working with pytest runner
- Other repos using pytest (sklearn, matplotlib, etc.) are unaffected

---

## Summary

### Question: Should baseline tests pass with ground truth patch in SWE-bench Verified?

**YES** - That's the entire point of "Verified". Each instance is verified to:
1. Tests fail before applying ground truth patch
2. Tests pass after applying ground truth patch
3. All PASS_TO_PASS tests continue passing

If baseline tests fail after these fixes, check:
- Container environment issues
- Missing dependencies
- Test setup problems specific to that instance

### Testing Recommendations

Test each repo type:
```bash
# Pytest repo
python scripts/submit_integrated_batch.py --repo "pytest-dev/pytest" --limit 1 --max-parallel 1

# Django repo
python scripts/submit_integrated_batch.py --repo "django/django" --limit 1 --max-parallel 1

# Sklearn (regression test)
python scripts/submit_integrated_batch.py --repo "scikit-learn/scikit-learn" --limit 1 --max-parallel 1
```

---

## Files Modified

1. `scripts/slurm/slurm_worker_integrated.py` - Fixed Docker image pattern (line 56)
2. `scripts/slurm/slurm_worker_analyze.py` - Fixed Docker image pattern (line 90)
3. `scripts/slurm/slurm_worker_build.py` - Fixed Docker image pattern (line 33)
4. `verifier/dynamic_analyzers/test_patch_singularity.py` - Added framework detection and Django support (lines 485-687)

---

## Issue 3: Git Clone Failures - Shallow Fetch Not Working

### Problem
Repository cloning was failing with exit code 128:
```
Command '['git', 'clone', '--depth', '1', 'https://github.com/pytest-dev/pytest.git', ...]' returned non-zero exit status 128.
```

Actually, the clone succeeded, but **checkout failed** because the specific commit wasn't fetched.

### Root Cause
The code used `git fetch --depth 1 origin <commit>` with `check=False`:
- If the shallow fetch **failed silently**, the code continued
- Then `git checkout <commit>` failed because the commit wasn't in history
- Exit code 128 = "commit not found"

Shallow fetch often fails for:
- Old commits
- Commits not on main branches
- Servers not supporting partial clone

### Solution
Added fallback logic in `swebench_integration/patch_loader.py` (lines 82-103):

1. Try shallow fetch first (faster): `git fetch --depth 1 origin <commit>`
2. If that fails, unshallow the repo: `git fetch --unshallow`
3. Then fetch the specific commit: `git fetch origin <commit>`
4. Finally checkout: `git checkout <commit>`

### Expected Impact
- Git clones should now succeed for all repos
- First clone: slightly slower (may need to unshallow)
- Subsequent operations: normal speed

---

## Summary of All Fixes

### Fixed Issues
1. ✅ **Docker image pattern** - pytest/django containers can now be pulled
2. ✅ **Test framework detection** - Django tests use correct test runner
3. ✅ **Git clone failures** - Shallow fetch has proper fallback

### Files Modified
1. `scripts/slurm/slurm_worker_integrated.py` - Docker image pattern (line 56)
2. `scripts/slurm/slurm_worker_analyze.py` - Docker image pattern (line 90)
3. `scripts/slurm/slurm_worker_build.py` - Docker image pattern (line 33)
4. `verifier/dynamic_analyzers/test_patch_singularity.py` - Framework detection (lines 485-687)
5. `swebench_integration/patch_loader.py` - Git fetch fallback (lines 82-103)

### Important Notes

**Python bytecode caching:** After making code changes, clear cache:
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -rm -rf
```

**Container build time:** First build takes 5-10 minutes (downloads 1-2GB image)

**Testing:** Run small batches first to verify:
```bash
python scripts/submit_integrated_batch.py --repo "pytest-dev/pytest" --limit 1
python scripts/submit_integrated_batch.py --repo "django/django" --limit 1
python scripts/submit_integrated_batch.py --repo "scikit-learn/scikit-learn" --limit 1
```

### Expected Baseline Test Pass Rates

After all fixes:
- **sklearn**: ~85% (already working)
- **django**: Should improve significantly (was 0%)
- **pytest**: Should improve significantly (was 0%)

If rates are still low, check for:
- Container environment issues
- Missing dependencies in containers
- Test-specific setup requirements
