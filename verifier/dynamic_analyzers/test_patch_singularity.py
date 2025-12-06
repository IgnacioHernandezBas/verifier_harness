# verifier/dynamic_analyzers/test_patch_singularity.py

"""
Patch evaluation on SWE-bench-style tasks using Singularity/Apptainer.

- Builds a minimal Python test image with Singularity.
- Clones & patches the target repo via PatchLoader.
- Applies model patch first, then test patch (if exists).
- Runs the SWE-bench FAIL_TO_PASS + PASS_TO_PASS tests inside the container.
- Returns a simple pass/fail result per prediction.

This file is self-contained and does NOT depend on the original SWE-bench
evaluation harness.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# -----------------------------
# Path setup (similar to syntax_structure.py)
# -----------------------------
CURRENT_DIR = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_DIR.parents[2]  # verifier/dynamic_analyzers → verifier → project root
sys.path.append(str(PROJECT_ROOT))

from swebench_integration.dataset_loader import DatasetLoader  # type: ignore
from swebench_integration.patch_loader import PatchLoader, PatchApplicationError  # type: ignore


# -----------------------------
# Singularity helpers
# -----------------------------
def build_singularity_image(
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
    python_version: str = "3.11",
    force_rebuild: bool = False,
) -> Path:
    """
    Build a minimal Singularity image with Python + pytest tooling.

    The image does NOT bake in any particular repo; we bind mount the patched repo
    at runtime under /workspace.

    Parameters
    ----------
    image_path : Path or str
        Path where the Singularity .sif image will be stored.
    python_version : str
        Python version tag for the base image (e.g. '3.11').
    force_rebuild : bool
        If True, rebuild even if image already exists.

    Returns
    -------
    Path
        Path to the built Singularity image.
    """
    image_path = Path(image_path)
    image_path.parent.mkdir(parents=True, exist_ok=True)

    if image_path.exists() and not force_rebuild:
        print(f"✅ Singularity image already exists: {image_path}")
        return image_path

    # Create a Singularity definition file
    singularity_def = f"""
Bootstrap: docker
From: python:{python_version}-slim

%post
    # Basic OS deps (git often useful for debugging, build tools for some deps)
    apt-get update
    apt-get install -y --no-install-recommends git build-essential
    rm -rf /var/lib/apt/lists/*

    # Core testing tooling; extend as needed
    pip install --no-cache-dir \\
        pytest \\
        pytest-xdist \\
        pytest-cov \\
        pytest-timeout \\
        hypothesis \\
        coverage

%environment
    export LC_ALL=C

%runscript
    exec "$@"
    """.strip() + "\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        def_file = tmpdir_path / "verifier-swebench.def"
        def_file.write_text(singularity_def, encoding="utf-8")

        # Remove old image if force rebuild
        if force_rebuild and image_path.exists():
            print(f"🗑️  Removing old image: {image_path}")
            image_path.unlink()

        # Set up Singularity temporary directories to avoid permission issues
        # Use accessible filesystem instead of compute-node-only scratch
        scratch_base = PROJECT_ROOT / "singularity_temp"
        singularity_tmp = scratch_base / "tmp"
        singularity_cache = scratch_base / "cache"
        singularity_tmp.mkdir(parents=True, exist_ok=True)
        singularity_cache.mkdir(parents=True, exist_ok=True)

        # Build environment with proper temp directories
        build_env = os.environ.copy()
        build_env["SINGULARITY_TMPDIR"] = str(singularity_tmp)
        build_env["SINGULARITY_CACHEDIR"] = str(singularity_cache)

        cmd = [
            "singularity",
            "build",
            "--fakeroot",  # Build without root privileges
            str(image_path),
            str(def_file),
        ]
        print(f"📦 Building Singularity image: {' '.join(cmd)}")
        print(f"   This may take several minutes on first build...")
        proc = subprocess.run(cmd, capture_output=True, text=True, env=build_env)

        if proc.returncode != 0:
            raise RuntimeError(
                "Failed to build Singularity image:\n"
                f"EXIT: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
            )
        else:
            print(f"✅ Singularity image built successfully: {image_path}")

    return image_path


def install_package_in_singularity(
    repo_path: Path,
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
) -> Dict[str, Any]:
    """
    Install the package and its dependencies inside the Singularity container.

    Detects setup.py, pyproject.toml, or setup.cfg and runs the appropriate install command.

    Since Singularity containers are read-only, we install to the user site-packages
    directory (~/.local) which is writable and persists across container runs.

    Parameters
    ----------
    repo_path : Path
        Local path to the repository.
    image_path : Path or str
        Singularity image to use.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr', 'installed'
    """
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Singularity image does not exist: {image_path}")

    # Check which setup files exist
    has_setup_py = (repo_path / "setup.py").exists()
    has_pyproject_toml = (repo_path / "pyproject.toml").exists()
    has_setup_cfg = (repo_path / "setup.cfg").exists()

    if not (has_setup_py or has_pyproject_toml or has_setup_cfg):
        # No setup files found, package might not need installation
        return {
            "returncode": 0,
            "stdout": "No setup files found, skipping installation",
            "stderr": "",
            "installed": False,
        }

    print(f"📦 Preparing package for testing in: {repo_path}")
    print(f"   Setup files found: setup.py={has_setup_py}, pyproject.toml={has_pyproject_toml}, setup.cfg={has_setup_cfg}")

    # For SWE-bench containers, copy pre-built C extensions from /testbed instead of building
    # This avoids Cython version compatibility issues
    print(f"   Copying pre-built C extensions from container...")

    copy_cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        str(image_path),
        "bash", "-c",
        "find /testbed -name '*.so' 2>/dev/null | while read f; do "
        "rel=$(echo $f | sed 's|/testbed/||'); "
        "mkdir -p /workspace/$(dirname $rel) 2>/dev/null; "
        "cp $f /workspace/$rel 2>/dev/null || true; "
        "done"
    ]

    copy_proc = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=60)

    if copy_proc.returncode == 0:
        # Count .so files to verify
        count_result = subprocess.run(
            ["find", str(repo_path), "-name", "*.so"],
            capture_output=True,
            text=True
        )
        so_count = len(count_result.stdout.strip().split('\n')) if count_result.stdout.strip() else 0

        # For matplotlib, also copy data files (mpl-data directory) and _version.py
        # Check if this is a matplotlib repo
        is_matplotlib = (repo_path / "lib" / "matplotlib").exists()
        if is_matplotlib:
            print(f"   Detected matplotlib, copying data files and _version.py...")
            mpl_files_cmd = [
                "singularity",
                "exec",
                "--bind", f"{str(repo_path)}:/workspace",
                str(image_path),
                "bash", "-c",
                "if [ -d /testbed/lib/matplotlib/mpl-data ]; then "
                "cp -r /testbed/lib/matplotlib/mpl-data /workspace/lib/matplotlib/ 2>/dev/null || true; "
                "fi; "
                "if [ -f /testbed/lib/matplotlib/_version.py ]; then "
                "cp /testbed/lib/matplotlib/_version.py /workspace/lib/matplotlib/ 2>/dev/null || true; "
                "fi"
            ]
            mpl_files_proc = subprocess.run(mpl_files_cmd, capture_output=True, text=True, timeout=60)
            version_exists = (repo_path / "lib" / "matplotlib" / "_version.py").exists()
            data_exists = (repo_path / "lib" / "matplotlib" / "mpl-data").exists()
            if mpl_files_proc.returncode == 0:
                if version_exists:
                    print(f"✅ Successfully copied matplotlib _version.py")
                if data_exists:
                    print(f"✅ Successfully copied matplotlib data files")

        if so_count > 0:
            print(f"✅ Successfully copied {so_count} pre-built C extension files")
            return {
                "returncode": 0,
                "stdout": f"Copied {so_count} .so files from /testbed",
                "stderr": "",
                "installed": True,
                "attempted": True,
                "build_method": "copy_from_testbed",
            }
        else:
            print(f"ℹ️  No C extensions found (pure Python package)")
            return {
                "returncode": 0,
                "stdout": "No C extensions to copy (pure Python package)",
                "stderr": "",
                "installed": False,
                "attempted": True,
                "pythonpath_mode": True,
            }

    # If copy failed, package might not need installation or /testbed doesn't exist
    print(f"ℹ️  No pre-built extensions available (will use PYTHONPATH mode)")
    return {
        "returncode": 0,
        "stdout": "No pre-built extensions available",
        "stderr": "",
        "installed": False,
        "attempted": True,
        "pythonpath_mode": True,
    }


def install_hypothesis_in_singularity(
    repo_path: Path,
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
) -> Dict[str, Any]:
    """
    Install hypothesis to a directory within the repo (writable and accessible in container).

    Since Singularity containers are read-only, we install hypothesis to a local directory
    within the bound repo path. This directory will be added to PYTHONPATH when running tests.

    Parameters
    ----------
    repo_path : Path
        Path to the repository (will be bound as /workspace in container).
    image_path : Path or str
        Singularity image to use.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr', 'installed', 'packages_dir'
    """
    repo_path = repo_path.resolve()
    image_path = Path(image_path)

    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"Singularity image does not exist: {image_path}")

    # Create a packages directory within the repo (writable and bound to container)
    packages_dir = repo_path / ".pip_packages"
    packages_dir.mkdir(exist_ok=True)

    # First, check if hypothesis is already installed in testbed or packages_dir
    check_cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        "--env", f"PYTHONPATH=/workspace/.pip_packages:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/python",
        "-c",
        "import hypothesis; print(hypothesis.__version__)",
    ]

    check_proc = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)

    if check_proc.returncode == 0:
        version = check_proc.stdout.strip()
        print(f"✅ Hypothesis already available (version {version})")
        return {
            "returncode": 0,
            "stdout": f"hypothesis {version} already installed",
            "stderr": "",
            "installed": True,
            "already_present": True,
            "packages_dir": str(packages_dir),
        }

    # Install hypothesis to the packages directory using --target
    # This installs to /workspace/.pip_packages which is writable (bound from host)
    cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/pip",
        "install",
        "--target", "/workspace/.pip_packages",
        "--no-cache-dir",
        "--quiet",
        "hypothesis",
    ]

    print(f"📦 Installing hypothesis to {packages_dir}...")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if proc.returncode == 0:
        print(f"✅ Hypothesis installed successfully to .pip_packages/")
    else:
        print(f"⚠️  Hypothesis installation had issues")
        print(f"   Return code: {proc.returncode}")
        print(f"   stderr: {proc.stderr[:400]}")

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "installed": proc.returncode == 0,
        "packages_dir": str(packages_dir),
    }


def install_pytest_cov_in_singularity(
    repo_path: Path,
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
) -> Dict[str, Any]:
    """
    Install pytest-cov to a directory within the repo for coverage collection.

    Since Singularity containers are read-only, we install pytest-cov to a local directory
    within the bound repo path. This directory will be added to PYTHONPATH when running tests.

    Parameters
    ----------
    repo_path : Path
        Path to the repository (will be bound as /workspace in container).
    image_path : Path or str
        Singularity image to use.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr', 'installed', 'packages_dir'
    """
    repo_path = repo_path.resolve()
    image_path = Path(image_path)

    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"Singularity image does not exist: {image_path}")

    # Create a packages directory within the repo (writable and bound to container)
    packages_dir = repo_path / ".pip_packages"
    packages_dir.mkdir(exist_ok=True)

    # Check if pytest-cov is already installed
    check_cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        "--env", f"PYTHONPATH=/workspace/.pip_packages:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/python",
        "-c",
        "import pytest_cov; print(pytest_cov.__version__)",
    ]

    check_proc = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)

    if check_proc.returncode == 0:
        version = check_proc.stdout.strip()
        print(f"✅ pytest-cov already available (version {version})")
        return {
            "returncode": 0,
            "stdout": f"pytest-cov {version} already installed",
            "stderr": "",
            "installed": True,
            "already_present": True,
            "packages_dir": str(packages_dir),
        }

    # Install pytest-cov and coverage to the packages directory
    # CRITICAL: Use --no-deps for pytest-cov to avoid installing pytest as a dependency
    # This prevents version conflicts when testing repos that provide their own pytest
    # (e.g., pytest repos have patched pytest in /workspace/src/pytest)

    # Step 1: Install coverage (pytest-cov's main dependency)
    coverage_cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/pip",
        "install",
        "--target", "/workspace/.pip_packages",
        "--no-cache-dir",
        "--quiet",
        "coverage",
    ]

    # Step 2: Install pytest-cov WITHOUT dependencies to avoid conflicts
    pytest_cov_cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/pip",
        "install",
        "--target", "/workspace/.pip_packages",
        "--no-cache-dir",
        "--no-deps",  # CRITICAL: Don't install pytest, pluggy, py, etc.
        "--quiet",
        "pytest-cov",
    ]

    print(f"📦 Installing pytest-cov to {packages_dir}...")

    # Install coverage first
    proc1 = subprocess.run(coverage_cmd, capture_output=True, text=True, timeout=60)
    if proc1.returncode != 0:
        print(f"⚠️  Coverage installation failed: {proc1.stderr[:200]}")

    # Then install pytest-cov without deps
    proc = subprocess.run(pytest_cov_cmd, capture_output=True, text=True, timeout=60)

    if proc.returncode == 0:
        print(f"✅ pytest-cov installed successfully to .pip_packages/")
    else:
        print(f"⚠️  pytest-cov installation had issues")
        print(f"   Return code: {proc.returncode}")
        print(f"   stderr: {proc.stderr[:400]}")

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "installed": proc.returncode == 0,
        "packages_dir": str(packages_dir),
    }


def run_tests_in_singularity(
    repo_path: Path,
    tests: List[str],
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
    extra_env: Optional[Dict[str, str]] = None,
    collect_coverage: bool = False,
    coverage_source: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run tests inside a Singularity container over the given repo.

    Automatically detects test framework (pytest vs Django) based on test format.

    Parameters
    ----------
    repo_path : Path
        Local path to the patched repository.
    tests : List[str]
        List of test identifiers. Format depends on framework:
        - Pytest: 'tests/test_foo.py::test_bar'
        - Django: 'test_name (module.Class)'
        If empty, runs tests over the whole suite.
    image_path : Path or str
        Singularity image to use.
    extra_env : Dict[str,str], optional
        Extra env vars to pass into the container.
    collect_coverage : bool, optional
        If True, collect code coverage using pytest-cov.
    coverage_source : str, optional
        Source directory to measure coverage for (default: /workspace).
        Can be a specific module path like 'sklearn' or 'django'.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr', 'coverage_file' (if collect_coverage=True)
    """
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Singularity image does not exist: {image_path}")

    # Detect test framework based on test format
    def detect_test_framework(test_list: List[str]) -> str:
        """Detect if tests are pytest or Django format."""
        if not test_list:
            return "pytest"  # default

        # Check first few tests
        for test in test_list[:5]:
            if "::" in test:
                return "pytest"
            elif "(" in test and ")" in test:
                return "django"

        return "pytest"  # default fallback

    def convert_django_test_name(test_str: str) -> str:
        """
        Convert Django unittest format to Django test command format.

        Input:  'test_ascii_validator (auth_tests.test_validators.UsernameValidatorsTests)'
        Output: 'auth_tests.test_validators.UsernameValidatorsTests.test_ascii_validator'
        """
        import re
        match = re.match(r'^(\w+)\s+\(([^)]+)\)$', test_str.strip())
        if match:
            test_method, test_class = match.groups()
            return f"{test_class}.{test_method}"
        return test_str  # fallback to original if parsing fails

    test_framework = detect_test_framework(tests)
    print(f"📝 Detected test framework: {test_framework}")

    # Check if C extensions already exist (from install_package_in_singularity)
    # If not, copy pre-built .so files from container's /testbed
    so_count = len(list(repo_path.glob("**/*.so")))

    if so_count == 0:
        print("📦 Copying pre-built C extensions from container...")
        copy_cmd = [
            "singularity",
            "exec",
            "--bind", f"{str(repo_path)}:/workspace",
            str(image_path),
            "bash", "-c",
            "find /testbed -name '*.so' 2>/dev/null | while read f; do "
            "rel=$(echo $f | sed 's|/testbed/||'); "
            "mkdir -p /workspace/$(dirname $rel) 2>/dev/null; "
            "cp $f /workspace/$rel 2>/dev/null || true; "
            "done"
        ]

        copy_proc = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=60)
        if copy_proc.returncode == 0:
            print("✓ C extensions copied")
        else:
            print("ℹ️  Could not copy C extensions (may not be needed)")
    else:
        print(f"ℹ️  Using existing C extensions ({so_count} files)")

    # Build environment variables for testbed Python
    # PYTHONPATH search order is CRITICAL for correctness:
    #
    # PROBLEM: When pytest-cov is installed to .pip_packages/, it also installs pytest
    # as a dependency. If .pip_packages comes first in PYTHONPATH, Python will import
    # the wrong pytest (from .pip_packages) instead of the patched pytest in /workspace.
    #
    # SOLUTION: Workspace paths must come BEFORE .pip_packages to ensure:
    # 1. Patched code (pytest/django/matplotlib/etc.) is loaded from /workspace first
    # 2. Testing tools (pytest-cov, hypothesis) fall through to .pip_packages only if
    #    not found in workspace (which is correct - they're auxiliary packages)
    #
    # This order is safe for all repos:
    # - pytest: Loads patched pytest from /workspace/src ✓
    # - django: Loads patched django from /workspace, pytest-cov from .pip_packages ✓
    # - matplotlib: Loads patched matplotlib from /workspace/lib, pytest-cov from .pip_packages ✓
    path_components = []

    # CRITICAL: Add workspace paths FIRST (before .pip_packages)
    # This ensures patched code always takes precedence

    # Add src directory FIRST for repos using src-layout (e.g., pytest)
    # In src-layout, packages are in /workspace/src/package_name/
    # No harm in adding /workspace/src even if empty - Python will skip it during imports
    if (repo_path / "src").exists() and (repo_path / "src").is_dir():
        path_components.append("/workspace/src")

    # Add workspace root
    path_components.append("/workspace")

    # Add lib directory for packages like matplotlib that use lib/ structure
    if (repo_path / "lib").exists() and (repo_path / "lib").is_dir():
        path_components.append("/workspace/lib")

    # Add .pip_packages LAST (for auxiliary testing tools like pytest-cov, hypothesis)
    # These should only be used if not found in workspace paths above
    if (repo_path / ".pip_packages").exists():
        path_components.append("/workspace/.pip_packages")

    python_path = ":".join(path_components)

    env_dict = {
        "PYTHONPATH": python_path,
    }
    if extra_env:
        env_dict.update(extra_env)

    # Singularity uses --env for environment variables
    env_args: List[str] = []
    for k, v in env_dict.items():
        env_args.extend(["--env", f"{k}={v}"])

    # Prepare test arguments based on framework
    if test_framework == "django":
        # Set Django settings module for Django's own test suite
        # This is required for running Django tests via 'python -m django test'
        if "DJANGO_SETTINGS_MODULE" not in env_dict:
            env_dict["DJANGO_SETTINGS_MODULE"] = "tests.test_sqlite"
            env_args.extend(["--env", "DJANGO_SETTINGS_MODULE=tests.test_sqlite"])
        # Convert Django test names
        converted_tests = [convert_django_test_name(t) for t in tests] if tests else []
        test_args = converted_tests

        # Build Django test arguments
        test_runner_args = []
        if verbose:
            test_runner_args.append("--verbosity=2")

        # Add coverage for Django if requested
        coverage_file = None
        if collect_coverage:
            # Clean up old coverage files
            old_coverage_db = repo_path / ".coverage"
            old_coverage_json = repo_path / ".coverage.json"
            if old_coverage_db.exists():
                old_coverage_db.unlink()
            if old_coverage_json.exists():
                old_coverage_json.unlink()

            coverage_file = repo_path / ".coverage.json"

            # For Django, we need to use coverage run command
            print(f"📊 Coverage collection enabled for Django tests")

        test_runner_args.extend(test_args)

        # Use Django's own test runner (tests/runtests.py) instead of 'python -m django test'
        # Django's repository has a custom test runner
        python_path_in_container = "/opt/miniconda3/envs/testbed/bin/python"

        if collect_coverage:
            # Run with coverage
            cov_source = coverage_source or "."
            cmd = [
                "singularity",
                "exec",
                "--bind", f"{str(repo_path)}:/workspace",
                "--pwd", "/workspace",
                *env_args,
                str(image_path),
                python_path_in_container,
                "-m",
                "coverage",
                "run",
                "--source", cov_source,
                "--branch",
                "tests/runtests.py",
                *test_runner_args,
            ]
        else:
            cmd = [
                "singularity",
                "exec",
                "--bind", f"{str(repo_path)}:/workspace",
                "--pwd", "/workspace",
                *env_args,
                str(image_path),
                python_path_in_container,
                "tests/runtests.py",
                *test_runner_args,
            ]

    else:  # pytest
        # If no specific tests are given, run full suite
        test_args = tests or []

        # No special handling needed for matplotlib test paths - they work as-is

        # Build pytest arguments
        pytest_args = ["-v"] if verbose else ["-q"]

        # Add coverage collection if requested
        coverage_file = None
        if collect_coverage:
            # Clean up old coverage files to prevent conflicts
            old_coverage_db = repo_path / ".coverage"
            old_coverage_json = repo_path / ".coverage.json"
            if old_coverage_db.exists():
                old_coverage_db.unlink()
            if old_coverage_json.exists():
                old_coverage_json.unlink()

            coverage_file = repo_path / ".coverage.json"
            cov_source = coverage_source or "/workspace"

            pytest_args.extend([
                f"--cov={cov_source}",
                "--cov-branch",  # Enable branch coverage tracking
                "--cov-report=term-missing:skip-covered",  # Show only uncovered lines in terminal
            ])

            print(f"📊 Coverage collection enabled for: {cov_source} (with branch coverage)")

        pytest_args.extend(test_args)

        # Use the container's testbed Python environment which has pytest pre-installed
        # This is the standard SWE-bench environment at /opt/miniconda3/envs/testbed
        python_path_in_container = "/opt/miniconda3/envs/testbed/bin/python"

        cmd = [
            "singularity",
            "exec",
            "--bind", f"{str(repo_path)}:/workspace",  # Mount repo
            "--pwd", "/workspace",  # Set working directory
            *env_args,
            str(image_path),
            python_path_in_container,
            "-m",
            "pytest",
            *pytest_args,
        ]

    print(f"🧪 Running {test_framework} tests in Singularity:\n  {' '.join(cmd)}\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }

    if collect_coverage:
        # pytest-cov creates .coverage file, convert it to JSON using coverage.py
        # The .coverage file is a binary SQLite database that coverage.py uses
        coverage_db = repo_path / ".coverage"

        if coverage_db.exists():
            # Convert .coverage to JSON using coverage command
            json_cmd = [
                "singularity",
                "exec",
                "--bind", f"{str(repo_path)}:/workspace",
                "--pwd", "/workspace",
                "--env", f"PYTHONPATH=/workspace/.pip_packages:/workspace",
                str(image_path),
                "/opt/miniconda3/envs/testbed/bin/python",
                "-m",
                "coverage",
                "json",
                "-o", "/workspace/.coverage.json",
            ]

            json_proc = subprocess.run(json_cmd, capture_output=True, text=True, timeout=120)

            if json_proc.returncode == 0 and coverage_file and coverage_file.exists():
                result["coverage_file"] = str(coverage_file)
                print(f"✓ Coverage data saved to: {coverage_file.name}")
            else:
                print(f"⚠️  Failed to convert coverage to JSON")
                if json_proc.stderr:
                    print(f"   stderr: {json_proc.stderr[:200]}")
                if json_proc.stdout:
                    print(f"   stdout: {json_proc.stdout[:200]}")
                result["coverage_file"] = None
        else:
            print(f"⚠️  Coverage database not generated (.coverage file missing)")
            result["coverage_file"] = None

    return result


def _install_dataclasses_if_needed(repo_path: Path, image_path: Path) -> None:
    """
    Install dataclasses backport if testbed Python < 3.7.

    The rules framework uses dataclasses which are built-in from Python 3.7+.
    For older Python versions, we install the backport to .pip_packages.
    """
    # Check Python version in testbed
    check_cmd = [
        "singularity", "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/python", "-c",
        "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))",
    ]

    try:
        proc = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            version_str = proc.stdout.strip()
            major, minor = map(int, version_str.split('.'))
            python_version = (major, minor)
        else:
            # Default to assuming Python 3.6
            python_version = (3, 6)
    except Exception:
        # If check fails, assume we need it
        python_version = (3, 6)

    # dataclasses is built-in from Python 3.7+
    if python_version >= (3, 7):
        return  # No need to install

    # Check if already installed
    pip_packages_dir = repo_path / ".pip_packages"
    if (pip_packages_dir / "dataclasses.py").exists():
        return  # Already installed

    # Install dataclasses backport
    pip_packages_dir.mkdir(exist_ok=True)

    install_cmd = [
        "singularity", "exec",
        "--bind", f"{str(repo_path)}:/workspace",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/pip", "install",
        "--target", "/workspace/.pip_packages",
        "--no-cache-dir", "--quiet",
        "dataclasses",
    ]

    subprocess.run(install_cmd, capture_output=True, text=True, timeout=60)


def run_rules_in_singularity(
    repo_path: Path,
    patch_str: str,
    rule_ids: Optional[List[str]] = None,
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
    verifier_harness_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run verification rules inside a Singularity container.

    This allows rules to load and execute code from packages with C extensions
    (like sklearn) that are built for the container environment.

    Parameters
    ----------
    repo_path : Path
        Local path to the patched repository.
    patch_str : str
        The unified diff patch string.
    rule_ids : List[str], optional
        List of rule IDs to run (e.g., ['rule_1', 'rule_2']). If None, runs all rules.
    image_path : Path or str
        Singularity image to use.
    verifier_harness_path : Path, optional
        Path to verifier_harness root. If None, uses current working directory.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr', 'results' (list of RuleResult dicts)
    """
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Singularity image does not exist: {image_path}")

    # Find verifier_harness root
    if verifier_harness_path is None:
        verifier_harness_path = Path.cwd()
    verifier_harness_path = verifier_harness_path.resolve()

    # Install dataclasses backport for Python 3.6 (needed for rules framework)
    # This is a no-op if Python >= 3.7 or if already installed
    _install_dataclasses_if_needed(repo_path, image_path)

    # Write patch to a temporary file in the repo
    patch_file = repo_path / ".patch_for_rules.diff"
    patch_file.write_text(patch_str, encoding='utf-8')

    # Determine which rules to run - CLI only accepts single rule or "all", not comma-separated
    rule_arg = "all" if rule_ids is None else "all"  # Always use "all" for now

    # Build the command to run rules inside the container
    # We need to:
    # 1. Mount both the repo and the verifier_harness code
    # 2. Set PYTHONPATH to include both
    # 3. Run the rules CLI

    # Use TESTBED Python to execute repo code dynamically
    # Rules require dataclasses (Python 3.7+), but we install the backport in .pip_packages
    # This allows rules to both use modern features AND execute repo C extensions
    python_path_components = [
        "/workspace/.pip_packages",  # Has dataclasses backport + pytest/hypothesis/etc.
        "/workspace",  # The repo being tested
        "/verifier_harness",  # Our rules code
    ]
    python_path = ":".join(python_path_components)

    # Build singularity command
    # Use TESTBED Python so we can execute repo code with its C extensions
    cmd = [
        "singularity",
        "exec",
        "--bind", f"{str(repo_path)}:/workspace",  # Mount repo
        "--bind", f"{str(verifier_harness_path)}:/verifier_harness",  # Mount our code
        "--pwd", "/workspace",  # Set working directory
        "--env", f"PYTHONPATH={python_path}",
        str(image_path),
        "/opt/miniconda3/envs/testbed/bin/python",  # Use testbed Python to execute repo code
        "-m", "verifier.rules.runner",
        "--rule", rule_arg,
        "--repo", "/workspace",
        "--patch-file", "/workspace/.patch_for_rules.diff",
    ]

    print(f"🔍 Running rules in Singularity container...")
    print(f"  Rules: {rule_arg}")
    print(f"  Repo: {repo_path.name}")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Clean up temp patch file
    if patch_file.exists():
        patch_file.unlink()

    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }

    # Parse JSON output from rules
    if proc.returncode == 0 or proc.stdout:
        try:
            # Rules output JSON to stdout
            results_json = json.loads(proc.stdout)

            # Handle both single rule (dict) and multiple rules (list) output
            if isinstance(results_json, dict):
                result["results"] = [results_json]
            else:
                result["results"] = results_json

            print(f"✓ Rules executed successfully: {len(result['results'])} rule(s) ran")

        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse rules JSON output: {e}")
            print(f"   stdout: {proc.stdout[:200]}")
            result["results"] = []
    else:
        print(f"⚠️  Rules execution failed (exit code {proc.returncode})")
        if proc.stderr:
            print(f"   Error: {proc.stderr[:400]}")
        result["results"] = []

    return result


# -----------------------------
# Core evaluation
# -----------------------------
def _index_dataset_by_instance_id(
    source: str = "princeton-nlp/SWE-bench_Verified",
    hf_mode: bool = True,
    split: str = "test",
) -> Dict[str, Dict[str, Any]]:
    """
    Load a SWE-bench-style dataset and build an index by instance_id.

    Assumes:
      - DatasetLoader puts non-core fields into sample["metadata"].
      - 'instance_id' lives in metadata["instance_id"] for HF SWE-bench.
    """
    loader = DatasetLoader(source=source, hf_mode=hf_mode, split=split)
    idx: Dict[str, Dict[str, Any]] = {}

    for sample in loader.iter_samples():
        metadata = sample.get("metadata", {})
        instance_id = metadata.get("instance_id")
        if instance_id:
            idx[instance_id] = sample

    return idx


def run_evaluation(
    predictions: List[Dict[str, Any]],
    image_path: Path | str = "/scratch/verifier_harness/verifier-swebench.sif",
    dataset_source: str = "princeton-nlp/SWE-bench_Verified",
    hf_mode: bool = True,
    split: str = "test",
    repos_root: Path | str | None = None,
    force_rebuild: bool = False,
) -> List[Dict[str, Any]]:
    """
    Evaluate model patches on SWE-bench-style tasks inside a Singularity container.

    This function is conceptually similar to SWE-bench's `run_evaluation`,
    but implemented entirely inside the verifier-harness repository.

    Parameters
    ----------
    predictions : list of dict
        Each dict must contain at least:
          - 'instance_id'
          - 'model_name_or_path'
          - 'model_patch' (unified diff string)
    image_path : Path or str
        Singularity image path to run tests in.
    dataset_source : str
        Source passed to DatasetLoader; default is HF SWE-bench Verified.
    hf_mode : bool
        Whether DatasetLoader should use HuggingFace mode.
    split : str
        Dataset split (e.g. 'test').
    repos_root : Path or str, optional
        Where to store cloned repos. Defaults to PROJECT_ROOT / "repos_temp".
    force_rebuild : bool
        If True, force rebuild of Singularity image.

    Returns
    -------
    List[Dict[str, Any]]
        Per-prediction results, including pass/fail and logs.
    """
    if repos_root is None:
        repos_root = PROJECT_ROOT / "repos_temp"
    repos_root = Path(repos_root)
    repos_root.mkdir(parents=True, exist_ok=True)

    # Ensure Singularity image exists
    image_path = build_singularity_image(image_path=image_path, force_rebuild=force_rebuild)

    # Build index of SWE-bench samples by instance_id
    instance_index = _index_dataset_by_instance_id(
        source=dataset_source,
        hf_mode=hf_mode,
        split=split,
    )

    results: List[Dict[str, Any]] = []

    for pred in predictions:
        instance_id = pred.get("instance_id")
        model_name = pred.get("model_name_or_path", "unknown-model")
        model_patch = pred.get("model_patch")

        if not instance_id or not model_patch:
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "invalid_prediction",
                    "error": "Missing instance_id or model_patch",
                }
            )
            continue

        sample = instance_index.get(instance_id)
        if sample is None:
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "missing_instance",
                    "error": f"Instance '{instance_id}' not found in dataset {dataset_source}",
                }
            )
            continue

        metadata = sample.get("metadata", {})
        test_patch_text: str = metadata.get("test_patch", "") or ""
        fail_to_pass = metadata.get("FAIL_TO_PASS", []) or []
        pass_to_pass = metadata.get("PASS_TO_PASS", []) or []

        # Handle string representations if needed
        if isinstance(fail_to_pass, str):
            import ast
            fail_to_pass = ast.literal_eval(fail_to_pass) if fail_to_pass else []
        if isinstance(pass_to_pass, str):
            import ast
            pass_to_pass = ast.literal_eval(pass_to_pass) if pass_to_pass else []

        # Prepare sample for PatchLoader (first apply model patch)
        patched_sample = dict(sample)
        patched_sample["patch"] = model_patch

        patcher = PatchLoader(
            patched_sample,
            repos_root=repos_root,
        )

        # Clean up any stale repos from previous runs
        try:
            patcher.cleanup_old_repos()
        except Exception as e:
            print(f"⚠️  Warning: failed to cleanup old repos: {e}")

        # Clone + apply model patch first
        try:
            patch_result = patcher.load_and_apply()
        except PatchApplicationError as e:
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "patch_application_failed",
                    "error": f"PatchApplicationError (model patch): {e}",
                }
            )
            continue
        except Exception as e:  # noqa: BLE001
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "patch_application_failed",
                    "error": f"Unexpected error applying model patch: {e}",
                }
            )
            continue

        # Apply test patch if it exists
        if test_patch_text.strip():
            try:
                test_patch_result = patcher.apply_additional_patch(test_patch_text)
                print(f"✅ Test patch applied: {test_patch_result.get('log', 'success')}")
            except PatchApplicationError as e:
                results.append(
                    {
                        "instance_id": instance_id,
                        "model_name_or_path": model_name,
                        "status": "test_patch_application_failed",
                        "error": f"PatchApplicationError (test patch): {e}",
                    }
                )
                continue
            except Exception as e:  # noqa: BLE001
                results.append(
                    {
                        "instance_id": instance_id,
                        "model_name_or_path": model_name,
                        "status": "test_patch_application_failed",
                        "error": f"Unexpected error applying test patch: {e}",
                    }
                )
                continue

        repo_path_str = patch_result.get("repo_path")
        if not repo_path_str:
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "patch_application_failed",
                    "error": f"PatchLoader did not return a repo_path. Log: {patch_result.get('log')}",
                }
            )
            continue

        repo_path = Path(repo_path_str)

        # Install package if needed (after patches are applied)
        print(f"📦 Checking if package installation is needed...")
        try:
            install_result = install_package_in_singularity(
                repo_path=repo_path,
                image_path=image_path,
            )
            if install_result.get("installed"):
                print(f"✅ Package installed successfully")
            else:
                print(f"ℹ️  Package installation skipped or not needed")
                # Debug: show why
                if install_result.get("returncode") != 0:
                    print(f"   Return code: {install_result.get('returncode')}")
                    print(f"   Stdout: {install_result.get('stdout', '')[:200]}")
                    print(f"   Stderr: {install_result.get('stderr', '')[:200]}")
        except Exception as e:
            print(f"⚠️  Warning: Package installation failed: {e}")
            # Continue anyway - some repos don't need installation

        # Tests according to SWE-bench completion definition
        tests_to_run = list(dict.fromkeys(fail_to_pass + pass_to_pass))

        # Run tests in Singularity
        test_result = run_tests_in_singularity(
            repo_path=repo_path,
            tests=tests_to_run,
            image_path=image_path,
        )

        passed = test_result["returncode"] == 0

        results.append(
            {
                "instance_id": instance_id,
                "model_name_or_path": model_name,
                "tests_run": tests_to_run,
                "returncode": test_result["returncode"],
                "passed": passed,
                "stdout": test_result["stdout"],
                "stderr": test_result["stderr"],
            }
        )

    return results


# -----------------------------
# Standalone Test Mode
# -----------------------------
if __name__ == "__main__":
    """
    Example standalone usage:

    - Uses HuggingFace 'princeton-nlp/SWE-bench_Verified' by default.
    - Evaluates a single sympy patch inside a Singularity container.
    - Prints a JSON report with pass/fail + logs.

    NOTE:
    -----
    For this example to work end-to-end, your HF dataset must contain
    an instance with 'instance_id' == 'sympy__sympy-20590', and the
    corresponding repo must be reachable and cloneable by PatchLoader.
    """

    predictions = [
        {
            "instance_id": "sympy__sympy-20590",
            "model_name_or_path": "gpt-4",
            "model_patch": (
                "diff --git a/sympy/core/sympify.py b/sympy/core/sympify.py\n"
                "index 6a73a83..fb90e1a 100644\n"
                "--- a/sympy/core/sympify.py\n"
                "+++ b/sympy/core/sympify.py\n"
                "@@ -508,7 +508,7 @@ def sympify(a, locals=None, convert_xor=True, strict=False, rational=False,\n"
                "         converter[type(a)],\n"
                "         (SympifyError,\n"
                "          OverflowError,\n"
                "-         ValueError)):\n"
                "+         ValueError, AttributeError)):\n"
                "     return a\n"
            ),
        }
    ]

    try:
        eval_results = run_evaluation(
            predictions=predictions,
            image_path="/scratch/verifier_harness/verifier-swebench.sif",
            dataset_source="princeton-nlp/SWE-bench_Verified",
            hf_mode=True,
            split="test",
        )
    except Exception as e:  # noqa: BLE001
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)

    print("\n📊 Evaluation results:")
    print(json.dumps(eval_results, indent=2))
