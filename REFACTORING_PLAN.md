# 🏗️ Comprehensive Refactoring Plan: Verifier Harness Project

**Date:** January 10, 2026
**Project:** verifier_harness (SWE-bench Patch Verification System)
**Current Status:** Production-ready but needs architectural cleanup
**Codebase Size:** 22,633 lines Python + 3.8MB notebooks

---

## 📊 Executive Summary

The verifier_harness project is a **functional and well-documented research system** that successfully evaluates AI-generated patches using static analysis, dynamic fuzzing, and supplementary verification rules. However, the codebase has accumulated technical debt from rapid development:

### Key Strengths ✅
- **Working system:** 194/500 SWE-bench instances supported (38.8%)
- **Baseline results:** 47% success rate on 300 test instances
- **Excellent documentation:** 20+ comprehensive guides
- **Modular architecture:** Clear separation of concerns

### Critical Issues 🔴
- **Security risk:** Hardcoded Docker credentials in git repository
- **Code duplication:** 1,115+ lines duplicated in Streamlit modules
- **Mixed organization:** External code integrated without clear boundaries
- **Large binary files:** 3.8MB of Jupyter notebooks in git history

---

## 🔍 Current State Analysis

### Codebase Statistics
```
Total Python Code:        22,633 lines
├── verifier/ (core)      17,000+ lines (75%)
├── scripts/ (CLI)         3,500+ lines (15%)
├── streamlit/ (UI)        2,076 lines (9%)
├── tests/                   500 lines (2%)
└── archive/                 752 lines (3%)

Configuration Files:           12
Documentation Files:           25+
Jupyter Notebooks:             5 (3.8MB)
SLURM Log Files:              50+
Result JSON Files:            200+
```

### Directory Structure (Current)
```
verifier_harness/
├── verifier/                    # Core verification engine ✅ GOOD
│   ├── static_analyzers/
│   ├── dynamic_analyzers/
│   ├── rules/ (9 verification rules)
│   └── utils/
│
├── scripts/                     # CLI entry points ✅ GOOD
│   ├── eval_cli.py
│   ├── run_swebench_instance.py
│   ├── submit_integrated_batch.py
│   └── slurm/
│
├── streamlit/                   # ⚠️ CODE DUPLICATION
│   └── modules/
│       └── static_eval/
│           └── static_modules/  # DUPLICATES verifier/static_analyzers/
│
├── swebench_integration/        # ⚠️ EMPTY FILES
│   ├── patch_runner.py          # 0 lines - empty
│   └── results_aggregator.py    # 0 lines - empty
│
├── swebench_singularity/        # ✅ GOOD - Container management
│
├── QuixBugs/                    # ⚠️ External dataset (empty submodule)
│
├── archive/                     # ⚠️ Deprecated but not removed
│   └── deprecated_code/
│
├── results/                     # ✅ Test results
├── slurm_logs/                  # ✅ Baseline test logs
├── papers/                      # ✅ Research references
├── docs/                        # ✅ Excellent documentation
└── analysis/                    # ⚠️ Large notebooks (1.3MB each)
```

---

## 📈 Baseline Test Results Summary

### SLURM Log Analysis (Job 5961820)
**Test Date:** December 16, 2025
**Experiment:** Claude 3.5 Sonnet patches on SWE-bench
**Test Duration:** 1 hour 6 minutes

```
Test Summary
=====================================
Total Instances Tested:    300
✅ Passed:                 141 (47.0%)
❌ Failed:                 159 (53.0%)
⚠️ Patch Apply Failed:      0 (0.0%)
⏭️ Skipped:                  0 (0.0%)

Success Rate:             47.00%
```

**Key Findings:**
- **Django:** High pass rate (~55% based on sample)
- **Astropy:** Mixed results (~40% pass rate)
- **No patch failures:** All patches applied cleanly
- **Container system:** Working reliably (Docker → Singularity conversion)

**Performance:**
- ~13 seconds per instance average
- 8 parallel jobs sustained
- No crashes or timeouts

---

## 🚨 Critical Issues Requiring Immediate Action

### 1. 🔥 SECURITY: Hardcoded Credentials
**Location:** `scripts/run_swebench_instance.py:44-49`

```python
DEFAULT_DOCKER_CREDS = {
    "APPTAINER_DOCKER_USERNAME": "nacheitor12",
    "APPTAINER_DOCKER_PASSWORD": "wN/^4Me%,!5zz_q",
}
```

**Impact:**
- ⚠️ Credentials exposed in git history (public if pushed)
- ⚠️ Violates security best practices
- ⚠️ Credential rotation requires code changes

**Priority:** 🔴 CRITICAL - Fix before any public push

---

### 2. 🔄 CODE DUPLICATION: Streamlit Modules

**Duplicated Files:**
```
verifier/static_analyzers/code_quality.py (443 lines)
    ↓↓↓ DUPLICATED ↓↓↓
streamlit/modules/static_eval/static_modules/code_quality.py (561 lines)

verifier/static_analyzers/syntax_structure.py (294 lines)
    ↓↓↓ DUPLICATED ↓↓↓
streamlit/modules/static_eval/static_modules/syntax_structure.py (294 lines)

verifier/utils/diff_utils.py
    ↓↓↓ DUPLICATED ↓↓↓
streamlit/modules/utils/diff_utils.py
```

**Impact:**
- 🐛 Bug fixes don't propagate automatically
- 🔧 Maintenance burden (2x effort for changes)
- 📊 1,115+ lines of unnecessary duplication

**Priority:** 🔴 HIGH - Fix during refactoring

---

### 3. 📁 UNCLEAR ORGANIZATION: External Code

**Issues:**
- `QuixBugs/` directory is empty (git submodule reference)
- External datasets mixed with project code
- No clear boundary between "our code" vs "external code"

**Priority:** 🟡 MEDIUM - Clarify in refactoring

---

### 4. 📦 REPOSITORY BLOAT

**Large Files in Git:**
```
results_analysis.ipynb                     1.3 MB
results_analysis_sklearn_only.ipynb        1.2 MB
fuzzing_pipeline_real_coverage.ipynb       144 KB
integrated_pipeline_modular.ipynb          108 KB
```

**Impact:**
- Slow git clone/pull operations
- Difficult to diff notebooks
- Binary data inflates repository size

**Priority:** 🟡 MEDIUM - Move to external storage or git-lfs

---

## 🎯 Detailed Refactoring Plan

### Phase 1: Security & Critical Fixes (1-2 days)
**Goal:** Eliminate security risks and critical bugs

#### Task 1.1: Remove Hardcoded Credentials 🔴 CRITICAL
**Files:** `scripts/run_swebench_instance.py`

**Steps:**
1. Create `.env.template` file:
   ```bash
   APPTAINER_DOCKER_USERNAME=your_username
   APPTAINER_DOCKER_PASSWORD=your_password
   ```

2. Update `scripts/run_swebench_instance.py`:
   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()

   DEFAULT_DOCKER_CREDS = {
       "APPTAINER_DOCKER_USERNAME": os.getenv("APPTAINER_DOCKER_USERNAME"),
       "APPTAINER_DOCKER_PASSWORD": os.getenv("APPTAINER_DOCKER_PASSWORD"),
   }
   ```

3. Add `.env` to `.gitignore`

4. Update documentation with new setup instructions

5. **CRITICAL:** Rotate exposed credentials immediately

**Verification:**
- ✓ No credentials in any `.py` files
- ✓ `.env` file in `.gitignore`
- ✓ Documentation updated

---

#### Task 1.2: Fix Empty/Incomplete Files
**Files:**
- `swebench_integration/patch_runner.py` (0 lines)
- `swebench_integration/results_aggregator.py` (0 lines)

**Steps:**
1. Determine if these are:
   - a) Work-in-progress (add TODO comments)
   - b) Obsolete (remove and update imports)

2. If WIP, add placeholder:
   ```python
   """
   TODO: Implement patch running functionality

   Planned features:
   - Load patches from dataset
   - Execute in isolated environment
   - Capture results
   """
   raise NotImplementedError("Module not yet implemented")
   ```

3. Update any imports that reference these modules

---

### Phase 2: Eliminate Code Duplication (2-3 days)
**Goal:** Single source of truth for all modules

#### Task 2.1: Refactor Streamlit Module Structure

**Current (Bad):**
```
streamlit/modules/static_eval/static_modules/code_quality.py  [DUPLICATE]
verifier/static_analyzers/code_quality.py                     [ORIGINAL]
```

**Proposed (Good):**
```
streamlit/modules/static_eval/code_quality_ui.py              [UI WRAPPER ONLY]
    ↓ imports from ↓
verifier/static_analyzers/code_quality.py                     [SINGLE SOURCE]
```

**Implementation:**

1. **Create UI wrapper** (`streamlit/modules/static_eval/code_quality_ui.py`):
   ```python
   """Streamlit UI wrapper for static code quality analysis"""
   import streamlit as st
   from verifier.static_analyzers.code_quality import (
       analyze_code_quality,
       DEFAULT_CHECKS,
       DEFAULT_WEIGHTS
   )

   def render_code_quality_ui(code_text: str):
       """Render Streamlit UI for code quality analysis"""
       st.subheader("Code Quality Analysis")

       # Use the actual verifier module
       results = analyze_code_quality(code_text)

       # UI-specific visualization logic only
       st.metric("Quality Score", results['score'])
       # ... more UI code ...
   ```

2. **Delete duplicate files:**
   ```bash
   rm streamlit/modules/static_eval/static_modules/code_quality.py
   rm streamlit/modules/static_eval/static_modules/syntax_structure.py
   rm streamlit/modules/utils/diff_utils.py
   ```

3. **Update Streamlit imports** throughout `streamlit/` directory

4. **Add `verifier/` to Python path** in Streamlit app:
   ```python
   # streamlit/app.py
   import sys
   from pathlib import Path

   # Add verifier to path
   sys.path.insert(0, str(Path(__file__).parent.parent / "verifier"))
   ```

**Benefits:**
- ✓ Single source of truth
- ✓ Bug fixes propagate automatically
- ✓ Reduces code by 1,115+ lines
- ✓ Clear separation: UI logic vs analysis logic

---

#### Task 2.2: Create Shared Utilities Module

**Goal:** Centralize common utilities used by multiple modules

**Create:** `verifier/common/` directory
```
verifier/common/
├── __init__.py
├── diff_utils.py      # Unified diff parsing (move from verifier/utils/)
├── file_utils.py      # File operations
├── logging_utils.py   # Logging configuration
└── config.py          # Shared configuration
```

**Migration:**
```bash
mv verifier/utils/diff_utils.py verifier/common/diff_utils.py
# Update all imports throughout codebase
```

---

### Phase 3: Reorganize Project Structure (3-4 days)
**Goal:** Clear boundaries between components

#### Task 3.1: Create New Directory Structure

**Proposed Structure:**
```
verifier_harness/
│
├── src/                           # All source code (NEW)
│   ├── verifier/                  # Core verification engine
│   │   ├── __init__.py
│   │   ├── static/                # Static analyzers
│   │   ├── dynamic/               # Dynamic fuzzing
│   │   ├── rules/                 # Supplementary rules (1-9)
│   │   └── common/                # Shared utilities
│   │
│   ├── swebench/                  # SWE-bench integration (RENAMED)
│   │   ├── __init__.py
│   │   ├── dataset.py             # Dataset loading
│   │   ├── patcher.py             # Patch application
│   │   ├── executor.py            # Test execution
│   │   └── containers/            # Container management (move from swebench_singularity/)
│   │
│   ├── cli/                       # CLI applications (RENAMED from scripts/)
│   │   ├── __init__.py
│   │   ├── eval_cli.py
│   │   ├── run_instance.py
│   │   ├── batch_processor.py
│   │   └── slurm/                 # SLURM workers
│   │
│   └── ui/                        # Streamlit UI (RENAMED from streamlit/)
│       ├── __init__.py
│       ├── app.py
│       └── components/            # UI components (no duplication)
│
├── tests/                         # Unit & integration tests
│   ├── unit/                      # Unit tests
│   │   ├── test_static_analyzers.py
│   │   ├── test_dynamic_fuzzing.py
│   │   └── test_rules/
│   │
│   └── integration/               # Integration tests
│       ├── test_pipeline.py
│       └── test_swebench.py
│
├── config/                        # Configuration files
│   ├── swebench_config.yaml
│   ├── logging.yaml
│   └── rules_config.yaml
│
├── docs/                          # Documentation
│   ├── api/                       # API documentation
│   ├── guides/                    # User guides
│   └── architecture/              # Architecture docs
│
├── data/                          # Data directory (gitignored)
│   ├── datasets/                  # External datasets
│   │   └── quixbugs/              # QuixBugs dataset (moved from QuixBugs/)
│   ├── results/                   # Test results
│   ├── cache/                     # Build cache
│   └── logs/                      # Execution logs
│
├── external/                      # External resources (gitignored)
│   ├── papers/                    # Research papers
│   └── containers/                # Container definitions
│
├── notebooks/                     # Jupyter notebooks (gitignored or git-lfs)
│   ├── analysis/
│   └── experiments/
│
├── .github/                       # GitHub workflows (NEW)
│   └── workflows/
│       ├── tests.yml
│       └── lint.yml
│
├── pyproject.toml                 # Modern Python project config (NEW)
├── setup.py                       # Package setup
├── requirements.txt               # Core dependencies
├── requirements-dev.txt           # Development dependencies (NEW)
├── .env.template                  # Environment variables template (NEW)
├── .gitignore                     # Git ignore patterns
├── .flake8                        # Flake8 config
├── .coveragerc                    # Coverage config
├── README.md                      # Main documentation
└── REFACTORING_PLAN.md           # This file
```

**Key Changes:**
1. **`src/` directory:** All source code in one place
2. **Renamed directories:** More descriptive names
   - `scripts/` → `src/cli/`
   - `streamlit/` → `src/ui/`
   - `swebench_integration/` + `swebench_singularity/` → `src/swebench/`
3. **`data/` directory:** All data files (gitignored)
4. **`external/` directory:** External resources (gitignored)
5. **`notebooks/` directory:** Analysis notebooks (gitignored or git-lfs)
6. **Clear imports:** `from src.verifier.static import analyze_code`

---

#### Task 3.2: Migration Script

**Create:** `scripts/migrate_to_new_structure.py`

```python
#!/usr/bin/env python3
"""
Migration script to reorganize project structure.

Usage:
    python scripts/migrate_to_new_structure.py --dry-run  # Preview changes
    python scripts/migrate_to_new_structure.py            # Execute migration
"""

import shutil
import os
from pathlib import Path

MIGRATIONS = [
    # (source, destination)
    ("verifier/", "src/verifier/"),
    ("scripts/", "src/cli/"),
    ("streamlit/", "src/ui/"),
    ("swebench_integration/", "src/swebench/"),
    ("swebench_singularity/", "src/swebench/containers/"),
    ("results/", "data/results/"),
    ("slurm_logs/", "data/logs/slurm/"),
    ("logs/", "data/logs/"),
    ("papers/", "external/papers/"),
    ("QuixBugs/", "data/datasets/quixbugs/"),
    ("analysis/", "notebooks/analysis/"),
    ("containers/", "external/containers/"),
]

def migrate(dry_run=True):
    """Execute migration"""
    for src, dst in MIGRATIONS:
        src_path = Path(src)
        dst_path = Path(dst)

        if not src_path.exists():
            print(f"⚠️ SKIP: {src} does not exist")
            continue

        if dry_run:
            print(f"📁 WOULD MOVE: {src} → {dst}")
        else:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            print(f"✅ MOVED: {src} → {dst}")

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Project Structure Migration")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    migrate(dry_run=dry_run)

    if dry_run:
        print("\n💡 Run without --dry-run to execute migration")
```

---

### Phase 4: Improve Configuration Management (1-2 days)
**Goal:** Centralized, environment-aware configuration

#### Task 4.1: Create `pyproject.toml`

**Create:** `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "verifier-harness"
version = "0.2.0"
description = "Unified verification system for AI-generated code patches"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
requires-python = ">=3.9"
license = {text = "MIT"}
readme = "README.md"
keywords = ["swe-bench", "verification", "fuzzing", "static-analysis"]

dependencies = [
    "hypothesis>=6.0.0",
    "coverage>=7.0.0",
    "pylint>=3.0.0",
    "flake8>=6.0.0",
    "radon>=6.0.0",
    "mypy>=1.0.0",
    "bandit>=1.7.0",
    "astroid>=3.0.0",
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
    "isort>=5.12.0",
    "pre-commit>=3.0.0",
]

ui = [
    "streamlit>=1.28.0",
    "plotly>=5.0.0",
    "pandas>=2.0.0",
]

slurm = [
    "spython>=0.3.0",
]

[project.scripts]
verifier-cli = "src.cli.eval_cli:main"
verifier-instance = "src.cli.run_instance:main"
verifier-batch = "src.cli.batch_processor:main"

[project.urls]
Homepage = "https://github.com/yourusername/verifier_harness"
Documentation = "https://github.com/yourusername/verifier_harness/tree/main/docs"
Repository = "https://github.com/yourusername/verifier_harness"

[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
  | data
  | external
)/
'''

[tool.isort]
profile = "black"
line_length = 100
skip = ["data", "external", ".venv"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "--cov=src --cov-report=html --cov-report=term-missing"

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
exclude = ["data/", "external/", "notebooks/"]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

---

#### Task 4.2: Environment Configuration System

**Create:** `src/verifier/common/config.py`

```python
"""
Centralized configuration management with environment-aware loading.
"""

import os
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration manager"""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    SRC_DIR = PROJECT_ROOT / "src"
    DATA_DIR = PROJECT_ROOT / "data"
    CONFIG_DIR = PROJECT_ROOT / "config"

    # Data subdirectories
    RESULTS_DIR = DATA_DIR / "results"
    CACHE_DIR = DATA_DIR / "cache"
    LOGS_DIR = DATA_DIR / "logs"
    DATASETS_DIR = DATA_DIR / "datasets"

    # Container settings
    DOCKER_USERNAME = os.getenv("APPTAINER_DOCKER_USERNAME")
    DOCKER_PASSWORD = os.getenv("APPTAINER_DOCKER_PASSWORD")
    SINGULARITY_CACHE_DIR = CACHE_DIR / "singularity"

    # Fuzzing settings
    HYPOTHESIS_MAX_EXAMPLES = int(os.getenv("HYPOTHESIS_MAX_EXAMPLES", "100"))
    FUZZING_TIMEOUT = int(os.getenv("FUZZING_TIMEOUT", "300"))

    # SLURM settings
    SLURM_PARTITION = os.getenv("SLURM_PARTITION", "cpu")
    SLURM_TIME_LIMIT = os.getenv("SLURM_TIME_LIMIT", "02:00:00")
    SLURM_MEMORY = os.getenv("SLURM_MEMORY", "8G")

    @classmethod
    def load_yaml_config(cls, config_name: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        config_path = cls.CONFIG_DIR / f"{config_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            return yaml.safe_load(f)

    @classmethod
    def ensure_directories(cls):
        """Create all required directories"""
        for dir_path in [
            cls.DATA_DIR,
            cls.RESULTS_DIR,
            cls.CACHE_DIR,
            cls.LOGS_DIR,
            cls.DATASETS_DIR,
            cls.SINGULARITY_CACHE_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
```

**Usage:**
```python
from src.verifier.common.config import Config

# Use configuration
results_dir = Config.RESULTS_DIR
docker_creds = {
    "username": Config.DOCKER_USERNAME,
    "password": Config.DOCKER_PASSWORD,
}
```

---

### Phase 5: Enhance Testing & Documentation (2-3 days)

#### Task 5.1: Expand Test Coverage

**Current:** Only 500 lines of tests (mostly rules)
**Goal:** 80%+ coverage of core modules

**Create test structure:**
```
tests/
├── unit/
│   ├── verifier/
│   │   ├── test_static_analyzers.py         # NEW
│   │   ├── test_patch_analyzer.py           # NEW
│   │   ├── test_test_generator.py           # NEW
│   │   ├── test_coverage_analyzer.py        # NEW
│   │   └── test_rules/
│   │       ├── test_rule_1.py               # EXISTS
│   │       └── ...
│   │
│   └── swebench/
│       ├── test_dataset.py                   # NEW
│       ├── test_patcher.py                   # NEW
│       └── test_containers.py                # NEW
│
└── integration/
    ├── test_evaluation_pipeline.py           # NEW
    ├── test_swebench_integration.py          # NEW
    └── fixtures/
        ├── sample_patches/
        └── expected_results/
```

**Example test:** `tests/unit/verifier/test_patch_analyzer.py`

```python
"""Tests for patch analysis functionality"""

import pytest
from src.verifier.dynamic.patch_analyzer import extract_changed_functions

def test_extract_changed_functions_simple():
    """Test extraction of changed functions from a simple patch"""
    patch = """
diff --git a/module.py b/module.py
--- a/module.py
+++ b/module.py
@@ -10,5 +10,6 @@ def calculate(x):
     return x * 2
+    # Added comment
"""

    result = extract_changed_functions(patch)

    assert len(result) == 1
    assert result[0]['function_name'] == 'calculate'
    assert result[0]['file_path'] == 'module.py'

def test_extract_changed_functions_multiple():
    """Test extraction with multiple changed functions"""
    # ... more tests ...
```

---

#### Task 5.2: Update Documentation

**Update/Create:**

1. **README.md** - Update with new structure
2. **docs/ARCHITECTURE.md** (NEW) - System architecture
3. **docs/API.md** (NEW) - API documentation
4. **docs/CONTRIBUTING.md** (NEW) - Contribution guidelines
5. **docs/DEPLOYMENT.md** (NEW) - Deployment guide

**Update existing guides:**
- Update all path references (scripts/ → src/cli/, etc.)
- Remove references to deprecated Podman executor
- Update QuixBugs setup instructions

---

### Phase 6: Repository Cleanup (1 day)

#### Task 6.1: Clean Up Git History

**Steps:**

1. **Move large notebooks to git-lfs:**
   ```bash
   # Install git-lfs
   git lfs install

   # Track large files
   git lfs track "notebooks/**/*.ipynb"
   git add .gitattributes

   # Migrate existing notebooks
   git lfs migrate import --include="notebooks/**/*.ipynb" --everything
   ```

2. **Remove sensitive data from history:**
   ```bash
   # Use BFG Repo-Cleaner or git-filter-repo
   git filter-repo --path scripts/run_swebench_instance.py --invert-paths
   # Then restore file without credentials
   ```

3. **Archive deprecated code properly:**
   ```bash
   # Create archive branch
   git checkout -b archive/deprecated-code
   git mv archive/ .
   git commit -m "Archive deprecated code"
   git checkout main
   git rm -rf archive/
   ```

---

#### Task 6.2: Update .gitignore

**Update:** `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# Environment variables
.env
.env.local
.env.*.local

# Data directories (NEW)
data/
external/
notebooks/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Containers
*.sif
singularity_temp/
overlay-layers/

# Logs
logs/
slurm_logs/
*.log
*.out
*.err

# Results
results/
*.json
!config/*.json

# Jupyter
.ipynb_checkpoints

# OS
.DS_Store
Thumbs.db

# Legacy (keep for backwards compatibility)
archive/
```

---

## 📋 Migration Checklist

### Pre-Migration
- [ ] Backup entire repository
- [ ] Document current working state
- [ ] Create migration branch
- [ ] Communicate with team

### Phase 1: Security (CRITICAL)
- [ ] Create .env.template
- [ ] Update credential loading code
- [ ] Add .env to .gitignore
- [ ] Rotate exposed credentials
- [ ] Test credential loading
- [ ] Verify no secrets in code

### Phase 2: Code Duplication
- [ ] Create UI wrapper files
- [ ] Update Streamlit imports
- [ ] Delete duplicate files
- [ ] Test Streamlit UI
- [ ] Run all tests

### Phase 3: Structure Reorganization
- [ ] Create new directory structure
- [ ] Run migration script (dry-run)
- [ ] Review migration plan
- [ ] Execute migration
- [ ] Update all imports
- [ ] Update documentation paths
- [ ] Run all tests

### Phase 4: Configuration
- [ ] Create pyproject.toml
- [ ] Create Config class
- [ ] Update all modules to use Config
- [ ] Test configuration loading
- [ ] Update environment setup docs

### Phase 5: Testing & Docs
- [ ] Write unit tests (target 80% coverage)
- [ ] Write integration tests
- [ ] Update README.md
- [ ] Create ARCHITECTURE.md
- [ ] Create API.md
- [ ] Update all guides

### Phase 6: Cleanup
- [ ] Set up git-lfs for notebooks
- [ ] Remove sensitive data from history
- [ ] Archive deprecated code
- [ ] Update .gitignore
- [ ] Clean up orphaned files

### Post-Migration
- [ ] Run full test suite
- [ ] Test on SLURM cluster
- [ ] Update CI/CD pipelines
- [ ] Deploy to production
- [ ] Monitor for issues

---

## 🎯 Success Criteria

### Code Quality
- ✓ No hardcoded credentials anywhere
- ✓ Zero code duplication
- ✓ 80%+ test coverage
- ✓ All tests passing
- ✓ Linting passes (flake8, pylint, mypy)

### Organization
- ✓ Clear directory structure
- ✓ Logical module boundaries
- ✓ Consistent import paths
- ✓ All external code separated

### Documentation
- ✓ Updated README.md
- ✓ Architecture documentation
- ✓ API documentation
- ✓ All guides updated

### Performance
- ✓ No performance regression
- ✓ Git clone time < 30 seconds
- ✓ Test suite runs < 5 minutes

---

## 🚀 Execution Timeline

**Total Estimated Time:** 10-15 days

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| 1. Security | 1-2 days | 🔴 CRITICAL | None |
| 2. Duplication | 2-3 days | 🔴 HIGH | Phase 1 |
| 3. Structure | 3-4 days | 🟡 MEDIUM | Phase 2 |
| 4. Configuration | 1-2 days | 🟡 MEDIUM | Phase 3 |
| 5. Testing/Docs | 2-3 days | 🟢 LOW | Phase 4 |
| 6. Cleanup | 1 day | 🟢 LOW | Phase 5 |

**Recommendation:** Execute phases sequentially, not in parallel, to avoid merge conflicts.

---

## 📝 Notes & Considerations

### QuixBugs Dataset
**Current State:** Empty directory (git submodule reference)

**Options:**
1. **Keep as submodule:** If you want to track upstream changes
2. **Move to data/datasets/:** If you only need a snapshot
3. **Remove entirely:** If not actively used

**Recommendation:** Move to `data/datasets/quixbugs/` and remove submodule. The dataset appears static (50+ programs evaluated), so tracking upstream changes is unnecessary.

---

### Streamlit UI Future
**Current:** Tightly coupled to main codebase
**Proposed:** Separate package (optional)

**Long-term option:** Extract Streamlit UI to separate repository:
```
verifier-harness/          # Core verification system
verifier-harness-ui/       # Streamlit web interface
```

**Benefits:**
- Independent deployment
- Separate dependencies
- Cleaner core package

**When:** After Phase 3 (structure reorganization)

---

### SLURM Integration
**Current:** Works well, no major issues

**Minor improvements:**
- Centralize SLURM configuration (move to config/)
- Add SLURM job templates
- Improve error handling in workers

**Priority:** LOW (not urgent)

---

## 🔧 Tools & Scripts Provided

### Migration Script
**File:** `scripts/migrate_to_new_structure.py` (included above)

**Usage:**
```bash
# Preview changes
python scripts/migrate_to_new_structure.py --dry-run

# Execute migration
python scripts/migrate_to_new_structure.py
```

### Import Update Script
**Create:** `scripts/update_imports.py`

```python
"""
Update import statements throughout codebase after reorganization.
"""

import re
from pathlib import Path

IMPORT_MAPPINGS = {
    'from verifier.': 'from src.verifier.',
    'from scripts.': 'from src.cli.',
    'from streamlit.': 'from src.ui.',
    'from swebench_integration.': 'from src.swebench.',
    'from swebench_singularity.': 'from src.swebench.containers.',
}

def update_file_imports(file_path: Path):
    """Update imports in a single file"""
    content = file_path.read_text()
    original = content

    for old_import, new_import in IMPORT_MAPPINGS.items():
        content = content.replace(old_import, new_import)

    if content != original:
        file_path.write_text(content)
        print(f"✓ Updated: {file_path}")
        return True
    return False

def main():
    """Update all Python files"""
    project_root = Path(__file__).parent.parent
    updated_count = 0

    for py_file in project_root.rglob("*.py"):
        if "venv" in str(py_file) or ".venv" in str(py_file):
            continue

        if update_file_imports(py_file):
            updated_count += 1

    print(f"\n✅ Updated {updated_count} files")

if __name__ == "__main__":
    main()
```

---

## 🎓 Lessons Learned & Best Practices

### What Went Well ✅
1. **Modular architecture:** Clear separation of concerns
2. **Comprehensive documentation:** 20+ guide files
3. **Working baseline:** 47% success rate on 300 instances
4. **Container system:** Reliable Docker → Singularity conversion

### What Needs Improvement ⚠️
1. **Code duplication:** Should have used imports from start
2. **Credentials management:** Never hardcode secrets
3. **Binary files in git:** Should have used git-lfs
4. **Directory structure:** Should have planned for growth

### Best Practices Going Forward 🎯
1. **Environment variables:** All secrets in .env
2. **Single source of truth:** Never duplicate code
3. **Git-lfs:** For binary files > 100KB
4. **Test-driven development:** Write tests first
5. **Configuration management:** Centralized config system
6. **Clear boundaries:** src/, data/, external/, docs/

---

## 📚 References

### Internal Documentation
- `docs/IMPLEMENTATION_SUMMARY.md` - Current implementation
- `docs/PIPELINE_OVERVIEW.md` - System overview
- `docs/RULES_ANALYSIS.md` - Verification rules
- `docs/SLURM_USAGE.md` - SLURM cluster guide

### External Resources
- [Python Packaging Guide](https://packaging.python.org/)
- [12-Factor App Methodology](https://12factor.net/)
- [SWE-bench Paper](papers/SWE-bench.pdf)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)

---

## ✅ Final Recommendations

### Immediate Actions (This Week)
1. 🔴 **Fix credentials** (Phase 1, Task 1.1) - CRITICAL
2. 🔴 **Remove duplicate code** (Phase 2, Task 2.1) - HIGH
3. 🟡 **Create pyproject.toml** (Phase 4, Task 4.1) - MEDIUM

### Short-term Actions (Next 2 Weeks)
4. 🟡 **Reorganize structure** (Phase 3) - MEDIUM
5. 🟡 **Expand tests** (Phase 5, Task 5.1) - MEDIUM
6. 🟢 **Update documentation** (Phase 5, Task 5.2) - LOW

### Long-term Actions (Next Month)
7. 🟢 **Repository cleanup** (Phase 6) - LOW
8. 🟢 **Consider UI separation** (see "Streamlit UI Future" section)

---

**End of Refactoring Plan**

*This document should be versioned and updated as refactoring progresses.*
