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
    image_path: Path | str = "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
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
        scratch_base = Path("/fs/nexus-scratch/ihbas/.singularity")
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
    image_path: Path | str = "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
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


def run_tests_in_singularity(
    repo_path: Path,
    tests: List[str],
    image_path: Path | str = "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Run pytest inside a Singularity container over the given repo.

    Parameters
    ----------
    repo_path : Path
        Local path to the patched repository.
    tests : List[str]
        List of pytest node ids (e.g. 'tests/test_foo.py::test_bar').
        If empty, runs 'pytest -q' over the whole suite.
    image_path : Path or str
        Singularity image to use.
    extra_env : Dict[str,str], optional
        Extra env vars to pass into the container.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr'
    """
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Singularity image does not exist: {image_path}")

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
    # PYTHONPATH allows import from workspace
    if (repo_path / "lib").exists() and (repo_path / "lib").is_dir():
        python_path = "/workspace/lib:/workspace"
    else:
        python_path = "/workspace"

    env_dict = {
        "PYTHONPATH": python_path,
    }
    if extra_env:
        env_dict.update(extra_env)

    # Singularity uses --env for environment variables
    env_args: List[str] = []
    for k, v in env_dict.items():
        env_args.extend(["--env", f"{k}={v}"])

    # If no specific tests are given, run full suite
    test_args = tests or []

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
        "-q",
        *test_args,
    ]

    print(f"🧪 Running tests in Singularity:\n  {' '.join(cmd)}\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


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
    image_path: Path | str = "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
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
            image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
            dataset_source="princeton-nlp/SWE-bench_Verified",
            hf_mode=True,
            split="test",
        )
    except Exception as e:  # noqa: BLE001
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)

    print("\n📊 Evaluation results:")
    print(json.dumps(eval_results, indent=2))
