# ⚡ Quick Action Plan - Start Here!

**Priority Actions for Cleaning Up Your Verifier Harness Project**

---

## 🚨 URGENT: Do This First (Today!)

### 1. Fix Security Issue (30 minutes)

**Problem:** Hardcoded Docker credentials in `scripts/run_swebench_instance.py`

**Fix:**
```bash
# Step 1: Create .env.template
cat > .env.template << 'EOF'
# Docker/Singularity credentials
APPTAINER_DOCKER_USERNAME=your_username_here
APPTAINER_DOCKER_PASSWORD=your_password_here
EOF

# Step 2: Create actual .env (with real credentials)
cp .env.template .env
# Edit .env and add your real credentials
nano .env  # or vim, or code .env

# Step 3: Add .env to .gitignore
echo "" >> .gitignore
echo "# Environment variables" >> .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Step 4: Install python-dotenv
pip install python-dotenv

# Step 5: Update the code
# See the code change below
```

**Code Change in `scripts/run_swebench_instance.py`:**

Replace lines 44-49:
```python
# BEFORE (REMOVE THIS):
DEFAULT_DOCKER_CREDS = {
    "APPTAINER_DOCKER_USERNAME": "nacheitor12",
    "APPTAINER_DOCKER_PASSWORD": "wN/^4Me%,!5zz_q",
}

# AFTER (ADD THIS):
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DEFAULT_DOCKER_CREDS = {
    "APPTAINER_DOCKER_USERNAME": os.getenv("APPTAINER_DOCKER_USERNAME"),
    "APPTAINER_DOCKER_PASSWORD": os.getenv("APPTAINER_DOCKER_PASSWORD"),
}

# Validate credentials are loaded
if not all(DEFAULT_DOCKER_CREDS.values()):
    raise ValueError(
        "Docker credentials not found. "
        "Please create a .env file from .env.template and add your credentials."
    )
```

**Test:**
```bash
python scripts/run_swebench_instance.py --instance_id matplotlib__matplotlib-23314 --build-only
```

**⚠️ IMPORTANT:** After this works, rotate your Docker credentials since they were exposed!

---

## 📋 This Week: High-Priority Tasks

### 2. Fix Code Duplication (2-3 hours)

**Problem:** Streamlit modules duplicate code from verifier/

**Files to fix:**
```
streamlit/modules/static_eval/static_modules/code_quality.py       [DELETE]
streamlit/modules/static_eval/static_modules/syntax_structure.py   [DELETE]
streamlit/modules/utils/diff_utils.py                              [DELETE]
```

**Solution:**

**Step 1:** Create UI wrapper (example for code_quality)

```python
# Create: streamlit/modules/static_eval/code_quality_ui.py

"""
Streamlit UI wrapper for code quality analysis.
This module provides UI components that use the core verifier functionality.
"""

import sys
from pathlib import Path

# Add verifier to path
VERIFIER_PATH = Path(__file__).parent.parent.parent.parent / "verifier"
sys.path.insert(0, str(VERIFIER_PATH))

# Import from core verifier (single source of truth)
from static_analyzers.code_quality import (
    analyze_code_quality,
    run_pylint,
    run_flake8,
    run_radon,
    run_mypy,
    run_bandit,
)

import streamlit as st


def render_code_quality_analysis(code: str, file_path: str = "temp.py"):
    """
    Render Streamlit UI for code quality analysis.

    Args:
        code: Python code to analyze
        file_path: Path to save temporary file (for analysis)
    """
    st.subheader("📊 Code Quality Analysis")

    # Run analysis using core verifier
    with st.spinner("Analyzing code quality..."):
        results = analyze_code_quality(code, file_path)

    # Display results in Streamlit UI
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overall Score", f"{results.get('overall_score', 0):.1f}/10")

    with col2:
        st.metric("Issues Found", results.get('total_issues', 0))

    with col3:
        st.metric("Security Issues", results.get('security_issues', 0))

    # Show detailed results
    if st.checkbox("Show Detailed Results"):
        st.json(results)

    return results
```

**Step 2:** Update imports in Streamlit app

```bash
# Find all files that import the duplicate modules
grep -r "from streamlit.modules.static_eval.static_modules" streamlit/

# Update each file to use the new UI wrapper
# Change:
#   from streamlit.modules.static_eval.static_modules.code_quality import analyze_code_quality
# To:
#   from streamlit.modules.static_eval.code_quality_ui import render_code_quality_analysis
```

**Step 3:** Delete duplicate files

```bash
rm -rf streamlit/modules/static_eval/static_modules/
rm -rf streamlit/modules/utils/
```

**Step 4:** Test

```bash
streamlit run streamlit/app.py
```

---

### 3. Clean Up Empty Files (15 minutes)

**Problem:** Two files exist but are empty

**Files:**
- `swebench_integration/patch_runner.py` (0 lines)
- `swebench_integration/results_aggregator.py` (0 lines)

**Option A: Add TODO placeholders** (if you plan to implement later)

```python
# swebench_integration/patch_runner.py

"""
Patch Runner Module

TODO: Implement patch execution functionality

Planned Features:
- Load patches from dataset
- Apply patches to repositories
- Execute tests in isolated environment
- Collect results

Status: Not yet implemented
"""

class PatchRunner:
    """Execute patches in isolated environment"""

    def __init__(self):
        raise NotImplementedError(
            "PatchRunner not yet implemented. "
            "Use scripts/run_swebench_instance.py instead."
        )

    def run_patch(self, instance_id: str):
        """Run a single patch"""
        raise NotImplementedError()
```

**Option B: Delete them** (if not needed)

```bash
# Check if anything imports these files
grep -r "from swebench_integration.patch_runner" .
grep -r "from swebench_integration.results_aggregator" .

# If no imports found, safe to delete
rm swebench_integration/patch_runner.py
rm swebench_integration/results_aggregator.py
```

---

### 4. Move Large Notebooks Out of Git (30 minutes)

**Problem:** 3.8MB of notebooks in git history

**Solution: Use git-lfs (Git Large File Storage)**

```bash
# Install git-lfs
git lfs install

# Track notebook files
git lfs track "*.ipynb"
git lfs track "analysis/*.ipynb"

# Add .gitattributes
git add .gitattributes

# Migrate existing notebooks to git-lfs
git lfs migrate import --include="*.ipynb" --everything

# Commit
git add .
git commit -m "chore: Move Jupyter notebooks to git-lfs"

# Note: This requires git-lfs to be installed on the server too
```

**Alternative: Move to external storage**

```bash
# Create external directory (gitignored)
mkdir -p external/notebooks

# Move notebooks
mv *.ipynb external/notebooks/
mv analysis/*.ipynb external/notebooks/

# Update .gitignore
echo "external/" >> .gitignore

# Commit removal
git add -A
git commit -m "chore: Move notebooks to external storage"
```

---

## 📅 Next Week: Structure Improvements

### 5. Create pyproject.toml (1 hour)

**Why:** Modern Python projects use pyproject.toml instead of setup.py

**Create `pyproject.toml`:**

```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "verifier-harness"
version = "0.2.0"
description = "Unified verification system for AI-generated code patches"
authors = [{name = "Your Name", email = "your.email@example.com"}]
requires-python = ">=3.9"
readme = "README.md"

dependencies = [
    "hypothesis>=6.0.0",
    "coverage>=7.0.0",
    "pylint>=3.0.0",
    "flake8>=6.0.0",
    "radon>=6.0.0",
    "mypy>=1.0.0",
    "bandit>=1.7.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "datasets>=2.0.0",
    "unidiff>=0.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
]
ui = [
    "streamlit>=1.28.0",
    "plotly>=5.0.0",
]

[project.scripts]
verifier-cli = "scripts.eval_cli:main"
verifier-instance = "scripts.run_swebench_instance:main"
```

**Test:**
```bash
pip install -e .
verifier-cli --help
```

---

### 6. Reorganize Directory Structure (4-6 hours)

**Goal:** Move to clean src/ structure

**Use the migration script** (see REFACTORING_PLAN.md for full script)

**Quick version:**

```bash
# Create new structure
mkdir -p src/{verifier,swebench,cli,ui}
mkdir -p data/{results,logs,cache,datasets}
mkdir -p external/{papers,containers}

# Move core modules
mv verifier/* src/verifier/
mv scripts/* src/cli/
mv streamlit/* src/ui/
mv swebench_integration/* src/swebench/
mv swebench_singularity/* src/swebench/containers/

# Move data
mv results/* data/results/
mv slurm_logs/* data/logs/
mv logs/* data/logs/
mv papers/* external/papers/
mv containers/* external/containers/

# Update .gitignore
echo "data/" >> .gitignore
echo "external/" >> .gitignore

# Update imports (run script from REFACTORING_PLAN.md)
python scripts/update_imports.py
```

---

## 🎯 Success Metrics

After completing these tasks, you should have:

### Security ✅
- [ ] No hardcoded credentials in code
- [ ] .env file in .gitignore
- [ ] Credentials rotated

### Code Quality ✅
- [ ] Zero code duplication
- [ ] No empty/incomplete files
- [ ] Clean import paths

### Repository ✅
- [ ] Git repo < 10MB
- [ ] No large binary files in history
- [ ] Clear structure (src/, data/, external/)

### Configuration ✅
- [ ] pyproject.toml created
- [ ] Modern Python packaging
- [ ] Easy installation (pip install -e .)

---

## 📚 Detailed Resources

For more details, see:

1. **REFACTORING_PLAN.md** - Complete refactoring guide (50+ pages)
2. **BASELINE_RESULTS_ANALYSIS.md** - Test results analysis
3. **REFACTORING_SUMMARY.md** - Before/after comparison

---

## ❓ FAQ

### Q: Do I need to do this all at once?
**A:** No! Start with security (item #1), then do items 2-4 when convenient. Items 5-6 can wait until next week.

### Q: Will this break my existing code?
**A:** Temporarily yes, but you'll fix imports as you go. The migration script helps automate this.

### Q: What if something goes wrong?
**A:** Create a backup branch first:
```bash
git checkout -b backup-before-refactoring
git checkout main
# Now do refactoring on main
```

### Q: How long will this take?
**A:**
- Security fix: 30 minutes
- Code duplication fix: 2-3 hours
- Full refactoring: 1-2 weeks

### Q: Can I skip the structure reorganization?
**A:** Yes, but your code will be harder to maintain. At minimum, do the security fix and remove code duplication.

---

## 🚀 Get Started Now!

```bash
# 1. Create a backup branch
git checkout -b backup-before-refactoring
git push origin backup-before-refactoring
git checkout main

# 2. Fix security issue (30 min)
# Follow steps in "URGENT: Do This First" above

# 3. Commit
git add .
git commit -m "security: Remove hardcoded credentials, use .env file"

# 4. Test
python scripts/run_swebench_instance.py --build-only --instance_id test

# 5. Continue with other tasks as time permits
```

---

## ✅ Checklist for Today

Copy this checklist and check off items as you complete them:

```
Today's Tasks (2-3 hours):
[ ] Create backup branch
[ ] Create .env.template
[ ] Create .env with real credentials
[ ] Add .env to .gitignore
[ ] Install python-dotenv
[ ] Update scripts/run_swebench_instance.py
[ ] Test credential loading
[ ] Commit security fix
[ ] Rotate Docker credentials (important!)

Optional (if time permits):
[ ] Fix code duplication in Streamlit
[ ] Add TODO comments to empty files
[ ] Move large notebooks out of git
```

---

**Good luck! Start with the security fix, and you'll have a much safer codebase in 30 minutes! 🔒**
