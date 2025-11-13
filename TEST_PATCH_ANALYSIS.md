# test_patch.py Analysis & Fixes

## Overview
The `test_patch.py` script is designed to evaluate model-generated patches on SWE-bench-style tasks using Podman containers. It:
1. Builds a Podman image with Python + pytest
2. Clones the target repository
3. Applies both test patches and model patches
4. Runs tests inside a container
5. Returns pass/fail results

## Issues Identified & Fixed

### 1. Critical: Temporary Directory on NFS (FIXED ✅)
**Location:** `test_patch.py:76`

**Problem:**
```python
with tempfile.TemporaryDirectory() as tmpdir:
```
This defaulted to `/fs/nexus-scratch/ihbas/podman_tmp/` which is on NFS. Podman's buildah requires extended attributes (xattr) which NFS doesn't support.

**Error:**
```
Error: lsetxattr operation not supported
```

**Solution:**
```python
# Use /tmp instead of default tmpdir to avoid NFS issues
local_tmpdir = Path("/tmp") / f"podman_build_{os.getpid()}"
local_tmpdir.mkdir(parents=True, exist_ok=True)

try:
    dockerfile_path = local_tmpdir / "Dockerfile"
    # ... build process ...

    # Set TMPDIR to /tmp to avoid NFS xattr issues
    build_env = os.environ.copy()
    build_env["TMPDIR"] = "/tmp"

    proc = subprocess.run(cmd, env=build_env, ...)
finally:
    # Clean up
    shutil.rmtree(local_tmpdir, ignore_errors=True)
```

### 2. Missing Image Existence Check (FIXED ✅)
**Location:** `test_patch.py:39-91`

**Problem:**
The script rebuilt the image on every run, wasting 30-60 seconds.

**Solution:**
```python
# Check if image already exists
try:
    check_cmd = ["podman", "image", "exists", image_name]
    result = subprocess.run(check_cmd, capture_output=True, timeout=10)
    if result.returncode == 0:
        print(f"✅ Image {image_name} already exists, skipping build.")
        return
except Exception as e:
    print(f"⚠️  Warning: could not check for existing image: {e}")
```

### 3. Missing Timeout on Subprocess Calls (FIXED ✅)
**Locations:** `test_patch.py:83, 149`

**Problem:**
No timeout on `subprocess.run()` could cause indefinite hangs.

**Solution:**
```python
# Added timeout parameter to build_podman_image()
def build_podman_image(
    image_name: str = "verifier-swebench:latest",
    python_version: str = "3.11",
    timeout: int = 600,  # NEW
) -> None:
    # ...
    proc = subprocess.run(cmd, timeout=timeout, ...)

# Added timeout to run_tests_in_podman()
def run_tests_in_podman(
    # ...
    timeout: int = 300,  # NEW
) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, timeout=timeout, ...)
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Test execution timed out after {timeout} seconds",
        }
```

### 4. Wrong Branch for Repository Cloning (FIXED ✅)
**Location:** `swebench_integration/patch_loader.py:68`

**Problem:**
PatchLoader always cloned with `-b main`, but many repos (like sympy) use `master` as their default branch.

**Error:**
```
Command '['git', 'clone', '--depth', '1', '-b', 'main', ...]' returned non-zero exit status 128.
```

**Solution:**
```python
# If we have a base_commit, clone without branch specification
# to avoid issues with different default branches (main vs master)
if self.base_commit:
    subprocess.run(
        ["git", "clone", "--depth", "1",
         self.base_repo_url, str(temp_dir)],
        check=True, capture_output=True,
    )
else:
    subprocess.run(
        ["git", "clone", "--depth", "1", "-b", self.branch,
         self.base_repo_url, str(temp_dir)],
        check=True, capture_output=True,
    )
```

## Current Workflow

### Step 1: Build Image
```
✅ Image verifier-swebench:latest already exists, skipping build.
```
Now properly checks for existing images and reuses them.

### Step 2: Clone & Patch
```
[+] Cloning sympy/sympy into /fs/nexus-scratch/ihbas/verifier_harness/repos_temp/sympy__sympy ...
```
Successfully clones repos without branch issues.

### Step 3: Apply Patch
This is where the current example fails due to a malformed patch in the hardcoded example.

### Step 4: Run Tests
Once patches apply correctly, tests run in the container:
```bash
podman run --rm -v /path/to/repo:/workspace:Z -w /workspace \
    -e PYTHONPATH=/workspace \
    verifier-swebench:latest \
    pytest -q test1.py test2.py
```

## Remaining Issues

### Issue 5: Repository Dependencies Not Installed ⚠️
**Problem:**
The base image only has pytest, but each repository has its own dependencies. Tests will fail if dependencies aren't installed.

**Current Approach:**
The image has basic tools:
```dockerfile
RUN pip install --no-cache-dir \
    pytest \
    pytest-xdist \
    hypothesis \
    coverage
```

**Potential Solutions:**

#### Option A: Install dependencies at runtime (Recommended)
Modify `run_tests_in_podman()` to:
1. Check for `requirements.txt`, `setup.py`, or `pyproject.toml`
2. Run pip install before pytest

```python
# Before running tests, install repo dependencies
install_cmd = [
    "podman", "run", "--rm",
    "-v", f"{str(repo_path)}:/workspace:Z",
    "-w", "/workspace",
    image_name,
    "bash", "-c",
    "pip install -e . 2>/dev/null || pip install -r requirements.txt 2>/dev/null || true"
]
subprocess.run(install_cmd, capture_output=True, timeout=300)
```

#### Option B: Build per-repo images
Build a custom image for each repo that includes dependencies. More correct but much slower.

#### Option C: Use SWE-bench environment specifications
SWE-bench provides `environment.yml` or `install.sh` scripts for each instance. Parse and use those.

### Issue 6: Example Patch Format
**Location:** `test_patch.py:382-395`

**Problem:**
The hardcoded example patch has formatting issues (missing context lines).

**Fix:**
Use a real patch from the dataset or fix the example:
```python
model_patch = """diff --git a/sympy/core/sympify.py b/sympy/core/sympify.py
index 6a73a83..fb90e1a 100644
--- a/sympy/core/sympify.py
+++ b/sympy/core/sympify.py
@@ -508,7 +508,7 @@ def sympify(a, locals=None, convert_xor=True, strict=False, rational=False,
             converter[type(a)],
             (SympifyError,
              OverflowError,
-             ValueError)):
+             ValueError, AttributeError)):
         return a
"""
```
Needs proper context lines and spacing.

## Testing Recommendations

### 1. Test with a Simple Repo First
Instead of sympy, test with a smaller repo:
```python
predictions = [
    {
        "instance_id": "test-instance",
        "model_name_or_path": "test",
        "model_patch": "# simple patch"
    }
]
```

### 2. Use Real SWE-bench Data
Load actual patches from the dataset instead of hardcoding:
```python
from swebench_integration.dataset_loader import DatasetLoader

loader = DatasetLoader(
    source="princeton-nlp/SWE-bench_Verified",
    hf_mode=True,
    split="test"
)

for sample in loader.iter_samples(limit=1):
    instance_id = sample["metadata"]["instance_id"]
    # Use real patch from dataset
```

### 3. Test Dependency Installation
Check if pytest can find modules:
```python
# Add to test output
extra_env = {
    "PYTHONPATH": "/workspace",
    "DEBUG": "1"
}
```

## Architecture Overview

```
test_patch.py
├── build_podman_image()          # Builds base image (FIXED)
├── run_tests_in_podman()         # Runs tests in container (FIXED)
└── run_evaluation()              # Main orchestrator
    ├── Loads dataset via DatasetLoader
    ├── For each prediction:
    │   ├── Combines test_patch + model_patch
    │   ├── Uses PatchLoader to clone + apply (FIXED)
    │   ├── Runs tests via run_tests_in_podman()
    │   └── Returns pass/fail results
    └── Returns JSON results
```

## Summary of Changes

### Files Modified:
1. `/fs/nexus-scratch/ihbas/verifier_harness/verifier/dynamic_analyzers/test_patch.py`
   - Fixed temp directory to use `/tmp` instead of NFS
   - Added image existence check
   - Added timeouts to subprocess calls
   - Added proper cleanup

2. `/fs/nexus-scratch/ihbas/verifier_harness/swebench_integration/patch_loader.py`
   - Fixed branch specification logic
   - Clone without branch when base_commit is available

### Test Results:
- ✅ Podman image builds successfully
- ✅ Image reuse works (skips rebuild)
- ✅ Repository cloning works
- ⚠️ Patch application needs valid patch format
- ⏳ Test execution (pending valid patch + dependencies)

## Next Steps

1. **Fix the example patch** - Use a real, valid patch from SWE-bench
2. **Add dependency installation** - Implement Option A above
3. **Test with real data** - Load actual SWE-bench instances
4. **Handle edge cases**:
   - Repos without tests
   - Test timeouts
   - Memory limits
   - Parallel execution

## Performance Notes

Current timing:
- Image build (first time): ~60s
- Image build (cached): <1s
- Repository clone: ~10-30s depending on size
- Test execution: Varies (30s-300s)

Expected total time per instance: 1-5 minutes

## Configuration Files Impact

These fixes align with the Podman configuration in `PODMAN_SETUP_GUIDE.md`:
- Storage: `/scratch0/ihbas/.containers/storage`
- Runtime: `/scratch0/ihbas/.containers/tmp`
- Build temp: `/tmp` (not on NFS)

This ensures builds work correctly on the Nexus cluster.
