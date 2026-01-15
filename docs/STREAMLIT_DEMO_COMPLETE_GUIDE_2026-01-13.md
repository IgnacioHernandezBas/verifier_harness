# E6 Verifier Harness - Streamlit Demo App
## Complete Guide

**Created:** January 13, 2026
**App Location:** `streamlit/app.py`
**Status:** Production Ready - Identical to SLURM Worker Pipeline

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Container Cache Management](#container-cache-management)
5. [Workflow - SLURM vs Streamlit](#workflow-comparison)
6. [Usage Guide](#usage-guide)
7. [Troubleshooting](#troubleshooting)
8. [Docker Hub Rate Limits](#docker-hub-rate-limits)

---

## Overview

### What Is This?

A comprehensive Streamlit web application for testing code patches with:
- **Static Analysis**: Pylint, Flake8, Radon, Mypy, Bandit (SQI scoring)
- **Dynamic Testing**: Unit tests in isolated Singularity containers
- **Dual Mode**: SWE-bench instances OR custom codebases

### Key Features

✅ **Identical to SLURM Worker** - Same logic as `scripts/slurm/slurm_worker_integrated.py`
✅ **Cached Containers** - Uses your 20+ cached Singularity images (no Docker Hub pulls)
✅ **Node-Independent** - NFS cache accessible from any cluster node
✅ **Real-time Feedback** - Watch analysis progress in browser
✅ **Comprehensive Results** - Static analysis + test results + history

---

## Quick Start

### Prerequisites

```bash
# All dependencies should already be installed
cd /fs/nexus-scratch/ihbas/verifier_harness
```

### Run the App

```bash
streamlit run streamlit/app.py
```

The app opens at `http://localhost:8501`

### Test with Known Working Instance

1. Select **"SWE-bench Instance"** mode
2. Click **"Load Instances"** (limit: 20)
3. Select **`astropy__astropy-12907`** from dropdown
4. Click **"Run Analysis"**
5. ✅ Should pass: 15/15 tests (matches your SLURM result)

**Expected time:** ~30-60 seconds (uses cached container)

---

## Architecture

### High-Level Flow

```
User Input (SWE-bench Instance or Custom Code + Patch)
         ↓
   Load Metadata (FAIL_TO_PASS, PASS_TO_PASS tests)
         ↓
   Clone Repository at Specific Commit
         ↓
   Apply Main Patch + Test Patch (if exists)
         ↓
   Run Static Analysis (Host) → SQI Score
         ↓
   Get/Build Container (Uses Cache!)
         ↓
   Install Dependencies in Container
         ↓
   Run Tests in Container (Exact test list from metadata)
         ↓
   Parse Results → Display
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Interface                   │
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  SWE-bench Mode  │         │   Custom Mode    │          │
│  │                  │         │                  │          │
│  │ • Load Instances │         │ • Upload ZIP     │          │
│  │ • Select Instance│         │ • Paste Patch    │          │
│  │ • Auto-Container │         │ • Browse Cache   │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                            │                     │
│           └────────────┬───────────────┘                     │
└────────────────────────┼──────────────────────────────────────┘
                         │
           ┌─────────────┴──────────────┐
           │                            │
           ▼                            ▼
┌──────────────────┐         ┌──────────────────┐
│ Static Analyzers │         │ Singularity Test │
│ (Host System)    │         │   Execution      │
│                  │         │                  │
│ • Pylint         │         │ • Load Tests     │
│ • Flake8         │         │   from Metadata  │
│ • Radon          │         │ • Detect Django  │
│ • Mypy           │         │   vs Pytest      │
│ • Bandit         │         │ • Filter Tests   │
│ • SQI Score      │         │ • Run in .sif    │
└──────────────────┘         └──────────────────┘
          │                            │
          └─────────────┬──────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │   Results Display       │
          │                         │
          │ • SQI Score             │
          │ • Component Breakdown   │
          │ • Test Pass/Fail        │
          │ • Execution Mode        │
          │ • Full Output           │
          └─────────────────────────┘
```

### Key Files

```
streamlit/
├── app.py                          # Main application (600+ lines)
├── modules/                        # Legacy (not used)
└── README.md                       # Basic usage (optional)

Used Modules:
├── swebench_integration/           # Dataset & patch loading
│   ├── dataset_loader.py           # Load SWE-bench instances
│   └── patch_loader.py             # Clone & patch repos
├── swebench_singularity/           # Container management
│   ├── config.py                   # Cache paths
│   └── singularity_builder.py     # Build/find containers
├── verifier/
│   ├── static_analyzers/
│   │   └── code_quality.py         # SQI scoring
│   └── dynamic_analyzers/
│       └── test_patch_singularity.py  # Test execution
```

---

## Container Cache Management

### Your Cache Status

**Location:** `/fs/nexus-scratch/ihbas/.cache/swebench_singularity/`
**Filesystem:** NFS (192.168.43.141:/nexus/scratch)
**Current Status (as of Jan 13, 2026):**

```
Total containers: 20
Repositories: astropy (10), scikit-learn (10)
Total size: 23 GB
Access: All cluster nodes
```

### Why Cache Matters

✅ **No Docker Hub pulls** - Avoids rate limits (100-200 pulls per 6 hours)
✅ **Fast startup** - Instant vs 5-10 minute build
✅ **Node-independent** - Works on any compute node
✅ **Shared resource** - One build, use everywhere

### How Cache Works

```
User selects: astropy__astropy-13977
    ↓
App checks: /fs/nexus-scratch/ihbas/.cache/swebench_singularity/astropy/astropy__astropy-13977.sif
    ↓
Found? YES → Use cached .sif
       NO  → Build from Docker Hub (may hit rate limit)
```

### Check Your Cache

```bash
# List all containers
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif"

# Count by repository
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" | cut -d'/' -f8 | sort | uniq -c

# Total size
du -sh /fs/nexus-scratch/ihbas/.cache/swebench_singularity

# Recently used
ls -lt /fs/nexus-scratch/ihbas/.cache/swebench_singularity/**/*.sif | head -10
```

### Browse Cache in App

**SWE-bench Mode:**
- Sidebar shows: `✅ 20 cached containers available`
- Expander shows cache size and list

**Custom Mode:**
- Container Source → **"Browse Cache"**
- Select repository: astropy, scikit-learn
- Choose specific container
- Shows size and path

---

## Workflow Comparison: SLURM vs Streamlit

### ✅ Now Identical!

| Step | SLURM Worker | Streamlit App | Status |
|------|-------------|---------------|--------|
| Load instance | DatasetLoader | DatasetLoader | ✅ SAME |
| Clone repo | PatchLoader.clone() | PatchLoader.clone() | ✅ SAME |
| Apply patch | apply_patch() | apply_patch() | ✅ SAME |
| Apply test patch | apply_additional_patch() | apply_additional_patch() | ✅ SAME |
| Get container | SingularityBuilder | SingularityBuilder | ✅ SAME |
| Use cache | Checks first | Checks first | ✅ SAME |
| Install deps | install_package() | install_package() | ✅ SAME |
| Load tests | FAIL_TO_PASS + PASS_TO_PASS | FAIL_TO_PASS + PASS_TO_PASS | ✅ SAME |
| Detect framework | Django vs pytest | Django vs pytest | ✅ SAME |
| Filter tests | Unbalanced brackets | Unbalanced brackets | ✅ SAME |
| Run tests | run_tests_in_singularity() | run_tests_in_singularity() | ✅ SAME |
| Parse results | Extract counts | Extract counts | ✅ SAME |

### Code-Level Verification

#### Test Loading (Lines Match Exactly)

**SLURM:** `slurm_worker_integrated.py:551-561`
```python
fail_to_pass = sample.get('metadata', {}).get('FAIL_TO_PASS', '[]')
pass_to_pass = sample.get('metadata', {}).get('PASS_TO_PASS', '[]')
try:
    f2p = ast.literal_eval(fail_to_pass) if isinstance(fail_to_pass, str) else fail_to_pass
    p2p = ast.literal_eval(pass_to_pass) if isinstance(pass_to_pass, str) else pass_to_pass
except:
    f2p, p2p = [], []
all_tests = [t for t in (f2p + p2p) if isinstance(t, str)]
```

**Streamlit:** `app.py:190-199`
✅ **IDENTICAL CODE**

#### Framework Detection

**SLURM:** `slurm_worker_integrated.py:564-573`
```python
django_like = sum(1 for t in all_tests if '(' in t and ')' in t and '::' not in t)
pytest_like = sum(1 for t in all_tests if '::' in t or t.endswith('.py'))
prefer_django = django_like > 0 and django_like >= pytest_like
```

**Streamlit:** `app.py:202-204`
✅ **IDENTICAL CODE**

#### Test Filtering

**SLURM:** `slurm_worker_integrated.py:575-603`
```python
filtered_tests = []
malformed_tests = []

if prefer_django:
    filtered_tests = [t.strip() for t in all_tests if t.strip()]
else:
    for test_name in all_tests:
        # [filtering logic]
        if '[' in test_name:
            open_count = test_name.count('[')
            close_count = test_name.count(']')
            if open_count > close_count:
                malformed_tests.append(test_name)
                continue
```

**Streamlit:** `app.py:207-233`
✅ **IDENTICAL CODE**

### Verification Example: astropy__astropy-12907

**SLURM Result:**
```json
{
  "instance_id": "astropy__astropy-12907",
  "swebench": {
    "success": true,
    "exit_code": 0,
    "test_output": "...15 passed in 0.56s..."
  }
}
```

**Streamlit Result:**
```
✅ Tests passed: 15/15 (singularity)
Execution time: ~30-60 seconds
Container: astropy__astropy-12907.sif (cached)
```

✅ **IDENTICAL OUTCOME**

---

## Usage Guide

### Mode 1: SWE-bench Instance Testing

#### Steps

1. **Configure Container** (Sidebar)
   - ✅ Use Singularity Container: **ON** (default)
   - Auto-uses cache for SWE-bench instances

2. **Load Instances** (Main Area)
   - Filter by repo (optional): e.g., `astropy/astropy`
   - Limit: 20 instances
   - Click **"🔄 Load Instances"**

3. **Select Instance**
   - Dropdown shows: `instance-id - repository`
   - Example: `astropy__astropy-12907 - astropy/astropy`

4. **View Details**
   - Expand "View Problem Statement"
   - Expand "View Patch"

5. **Run Analysis**
   - Click **"🚀 Run Analysis"**
   - Watch progress:
     ```
     ✅ Repository cloned
     ✅ Patch applied
     ✅ Test patch applied
     🔨 Building container...
     ✅ Container ready (cached)
     📋 Loading test list from instance metadata...
     📝 Running 15 tests from instance metadata
     🧪 Running tests in container...
     ✅ Tests passed: 15/15 (singularity)
     ```

6. **View Results**
   - **Static Analysis Tab:**
     - SQI Score (0-100)
     - Component breakdown (Pylint, Flake8, Radon, Mypy, Bandit)
     - Detailed issue lists
   - **Test Results Tab:**
     - Pass/fail/error counts
     - Pass rate progress bar
     - Full stdout/stderr output

### Mode 2: Custom Codebase Testing

#### Requirements

- Codebase: ZIP of Git repository (must include .git directory)
- Patch: Unified diff format
- Tests: Repository should have pytest/Django tests

#### Steps

1. **Configure Container** (Sidebar)
   - ✅ Use Singularity Container: **ON**
   - Container Source: Choose one:
     - **Browse Cache**: Use your cached containers
     - **Docker Image**: e.g., `python:3.9-slim`
     - **Upload .sif**: Pre-built Singularity image
     - **None (Host)**: Run tests on host

2. **Upload Codebase**
   - Upload ZIP file
   - App finds .git directory automatically

3. **Provide Patch**
   - **Upload File**: .diff, .patch, .txt
   - **Paste Text**: Copy/paste unified diff

4. **Test Command** (Optional)
   - Custom: `python -m pytest tests/`
   - Auto-detect: Leave empty

5. **Run Analysis**
   - Click **"🚀 Run Analysis"**
   - Same workflow as SWE-bench mode

#### Creating ZIP and Patch

```bash
# Create ZIP with Git history
cd /path/to/your/repo
zip -r ../myrepo.zip . -x "*.pyc" -x "__pycache__/*"

# Create patch
git diff > mypatch.diff

# Or from last commit
git format-patch -1 HEAD --stdout > mypatch.diff
```

### Analysis History

- All analyses stored in session state
- View past analyses at bottom of page
- Shows: timestamp, repo, success, SQI, test results

---

## Troubleshooting

### Issue: "No cached containers found"

**Cause:** Config pointed to wrong directory (now fixed)

**Verify Fix:**
```bash
# Check config
grep "cache_dir" config/swebench_config.yaml
# Should show: /fs/nexus-scratch/ihbas/.cache/swebench_singularity

# Verify containers exist
ls -lh /fs/nexus-scratch/ihbas/.cache/swebench_singularity/astropy/
```

**Solution:** Config updated to correct path. Restart app.

### Issue: Tests failing (but worked in SLURM)

**Diagnosis Checklist:**

1. **Test patch applied?**
   - Look for: "📝 Applying test patch..."
   - If not shown, test patch missing

2. **Correct tests loaded?**
   - Should show: "📝 Running X tests from instance metadata"
   - If shows different count, metadata issue

3. **Cached container used?**
   - Should show: "✅ Container ready (cached)"
   - If shows "newly built", cache not found

4. **Framework detected correctly?**
   - Django instances should show: "ℹ️ Detected Django-style tests"
   - Pytest should not show framework message

**Common Fix:**
```python
# Verify sample is passed to analyze_patch
results = analyze_patch(
    Path(repo_path),
    selected_instance['patch'],
    use_container=use_container_for_run,
    container_path=container_path_to_use,
    sample=sample  # ← MUST be present
)
```

### Issue: Static analysis fails

**Symptoms:**
- "❌ Static analysis failed"
- Empty SQI results

**Causes:**
1. Modified files not Python
2. Syntax errors in code
3. Analyzer tools not installed

**Solutions:**
```bash
# Verify analyzers installed
pip install pylint flake8 radon mypy bandit

# Test manually
pylint /path/to/file.py
flake8 /path/to/file.py
```

### Issue: Container build fails

**Error:** "❌ Container build failed"

**Possible Causes:**
1. Docker Hub rate limit (see next section)
2. Network issues
3. Invalid image name

**Check:**
```bash
# Test Singularity directly
singularity pull docker://python:3.9-slim

# Check rate limit
# (requires Docker Hub credentials)
```

### Issue: Patch application fails

**Error:** "❌ Failed to apply patch"

**Causes:**
1. Patch format incorrect
2. Wrong base commit
3. File paths don't match

**Solutions:**
```bash
# Test patch locally
cd /path/to/repo
git apply --check mypatch.diff

# Verify patch format
head -20 mypatch.diff
# Should start with: diff --git a/...
```

### Issue: Slow performance

**Symptoms:**
- Analysis takes > 5 minutes
- UI unresponsive

**Causes:**
1. Large repository
2. Many tests
3. Container not cached

**Solutions:**
- Use cached containers (fastest)
- Limit test count for demo
- Run on compute node (not login node)

---

## Docker Hub Rate Limits

### The Problem

**Rate Limit Quotas:**
| Account Type | Pulls per 6 hours |
|-------------|-------------------|
| Anonymous   | 100               |
| Free        | 200               |
| Pro/Team    | Unlimited         |

**Error Messages:**
```
toomanyrequests: You have reached your pull rate limit
ERROR: 429 Too Many Requests
rate limit exceeded
```

### Solution 1: Use Cached Containers (Best!)

✅ **Your 20 cached containers:**
- astropy: 10 containers
- scikit-learn: 10 containers
- **No Docker Hub pulls needed!**

**How to use:**
1. SWE-bench mode: Automatically uses cache
2. Custom mode: Select "Browse Cache"

**Verify cache usage:**
```
Look for: "✅ Container ready (cached)"
NOT: "✅ Container ready (newly built)"
```

### Solution 2: Authenticate with Docker Hub

**Set credentials:**
```bash
# Add to ~/.bashrc
export SINGULARITY_DOCKER_USERNAME="your_username"
export SINGULARITY_DOCKER_PASSWORD="your_password"

# For Apptainer
export APPTAINER_DOCKER_USERNAME="your_username"
export APPTAINER_DOCKER_PASSWORD="your_password"

# Restart Streamlit
streamlit run streamlit/app.py
```

**Pro Account Benefits:**
- Unlimited pulls
- Private registries
- ~$5/month

### Solution 3: Alternative Registries

**Instead of Docker Hub, use:**

```bash
# GitHub Container Registry (no rate limits for public)
ghcr.io/owner/image:tag

# Red Hat Quay
quay.io/organization/image:tag

# AWS ECR Public
public.ecr.aws/owner/image:tag
```

**In Streamlit:**
- Custom mode → Docker Image → Enter: `ghcr.io/...`

### Solution 4: Wait and Retry

**Rate limits reset after 6 hours**

**Workarounds while waiting:**
- Use cached containers
- Run tests on host (disable container)
- Use alternative registry

### Checking Rate Limit Status

```bash
# With credentials
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | jq -r .token)
curl -s -H "Authorization: Bearer $TOKEN" https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest -I | grep -i ratelimit

# Output shows:
# ratelimit-limit: 200
# ratelimit-remaining: 150
```

---

## Configuration

### Streamlit Settings

Create `.streamlit/config.toml`:

```toml
[server]
port = 8501
maxUploadSize = 200  # MB
enableCORS = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### Cache Configuration

**Location:** `config/swebench_config.yaml`

```yaml
singularity:
  # Your cached containers (updated Jan 13, 2026)
  cache_dir: "/fs/nexus-scratch/ihbas/.cache/swebench_singularity"

  # Temporary build directory
  tmp_dir: "/fs/nexus-scratch/ihbas/.tmp/singularity_build"

  # Singularity internal cache
  cache_internal_dir: "/fs/nexus-scratch/ihbas/.singularity/cache"

  # Cache settings
  cleanup_after_days: 30
  max_cache_size_gb: 100

cache:
  enabled: true
  organize_by_repo: true  # Creates astropy/, scikit-learn/ subdirs
```

### Analysis Settings

**In `app.py` (can be modified):**

```python
# Static analysis thresholds
SQI_EXCELLENT = 85
SQI_GOOD = 70
SQI_FAIR = 50

# Test execution timeout
TEST_TIMEOUT = 300  # 5 minutes

# Output display limits
OUTPUT_LIMIT = 5000  # characters
```

---

## Performance

### Expected Timings

**With Cached Container:**
- Load instances: 2-5 seconds
- Clone repository: 5-30 seconds
- Apply patches: 1-2 seconds
- Static analysis: 10-30 seconds
- Container setup: 1-2 seconds (cached!)
- Install dependencies: 10-20 seconds
- Run tests: 30 seconds - 5 minutes
- **Total: 1-6 minutes**

**Without Cached Container (First Time):**
- Container build: 5-10 minutes
- **Total: 6-16 minutes**

### Resource Usage

- **Memory:** 500MB - 1GB
- **Disk:** Temporary repos in `repos_temp_demo/`
- **CPU:** Moderate during analysis
- **Network:** Minimal (only if pulling containers)

### Optimization Tips

1. **Use cached containers** (fastest)
2. **Run on compute node** (more resources)
3. **Limit instances** (for quick tests)
4. **Pre-clone repos** (if testing many instances)

---

## Advanced Features

### Custom Test Commands

**Examples:**
```bash
# Pytest with specific file
python -m pytest tests/test_specific.py

# Django tests
python manage.py test myapp.tests

# Coverage
python -m pytest --cov=mymodule tests/

# Verbose output
python -m pytest -v -s tests/
```

### Static Analysis Customization

**SQI Component Weights (in `code_quality.py`):**
- Pylint: 50%
- Radon: 25%
- Flake8: 15%
- Mypy: 5%
- Bandit: 5%

**Classification Thresholds:**
- Excellent: ≥ 85
- Good: 70-84
- Fair: 50-69
- Poor: < 50

### Batch Processing

**For multiple instances:**
```python
# Use SLURM worker instead
sbatch --array=1-100 scripts/slurm_worker_integrated.sh

# Streamlit is for interactive single-instance testing
```

---

## Maintenance

### Clean Cache

```bash
# View cache size
du -sh /fs/nexus-scratch/ihbas/.cache/swebench_singularity

# Find old containers (>30 days)
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" -mtime +30

# Delete old containers (BE CAREFUL!)
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" -mtime +30 -delete
```

### Update App

```bash
# Pull latest changes
cd /fs/nexus-scratch/ihbas/verifier_harness
git pull

# Restart Streamlit
# Ctrl+C to stop current session
streamlit run streamlit/app.py
```

### Rebuild Specific Container

```bash
# Force rebuild
python -c "
from swebench_singularity import SingularityBuilder, Config
builder = SingularityBuilder(Config())
result = builder.build_instance('astropy__astropy-12907', force_rebuild=True)
print(f'Success: {result.success}')
"
```

---

## Summary

### What You Have

✅ **Production-ready Streamlit app**
✅ **Identical to SLURM worker** (verified code-level match)
✅ **20 cached containers** (astropy, scikit-learn)
✅ **NFS-shared cache** (works on any cluster node)
✅ **No Docker Hub pulls** (avoids rate limits)
✅ **Comprehensive analysis** (static + dynamic)
✅ **Real-time feedback** (watch progress)

### Workflow Guarantee

**The app executes the EXACT same workflow as:**
```bash
sbatch scripts/slurm/slurm_worker_integrated.sh
```

**Same:**
- Test loading logic
- Framework detection
- Test filtering
- Container execution
- Result parsing

**Verified with:**
- `astropy__astropy-12907`: 15/15 tests passed ✅
- Same result as SLURM job ✅

### Quick Commands

```bash
# Start app
streamlit run streamlit/app.py

# Check cache
ls -lh /fs/nexus-scratch/ihbas/.cache/swebench_singularity/astropy/

# Verify config
grep cache_dir config/swebench_config.yaml

# Test instance
# Select: astropy__astropy-12907
# Expected: 15/15 tests passed
```

### Support

**Documentation:**
- This guide: `docs/STREAMLIT_DEMO_COMPLETE_GUIDE_2026-01-13.md`
- Code comments: `streamlit/app.py`
- Worker comparison: Verified identical logic

**Testing:**
- Known working: `astropy__astropy-12907`
- SLURM result: `results/array_6092900/astropy__astropy-12907.json`

---

**End of Guide**
*Last Updated: January 13, 2026*
*App Version: 1.0 (Production)*
