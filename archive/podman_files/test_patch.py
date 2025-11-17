# verifier/dynamic_analyzers/test_patch.py

"""
Patch evaluation on SWE-bench-style tasks using Podman.

- Builds a minimal Python test image with Podman.
- Clones & patches the target repo via PatchLoader.
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
# Podman helpers
# -----------------------------
def build_podman_image(
    image_name: str = "verifier-swebench:latest",
    python_version: str = "3.11",
) -> None:
    """
    Build a minimal Podman image with Python + pytest tooling.

    The image does NOT bake in any particular repo; we mount the patched repo
    at runtime under /workspace.

    Parameters
    ----------
    image_name : str
        Tag to give the resulting Podman image.
    python_version : str
        Python version tag for the base image (e.g. '3.11-slim').
    """
    dockerfile = f"""
    FROM python:{python_version}-slim

    # Basic OS deps (git often useful for debugging, build tools for some deps)
    RUN apt-get update \\
        && apt-get install -y --no-install-recommends git build-essential \\
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /workspace

    # Core testing tooling; extend as needed
    RUN pip install --no-cache-dir \\
        pytest \\
        pytest-xdist \\
        hypothesis \\
        coverage

    CMD ["bash"]
    """.strip() + "\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        dockerfile_path = tmpdir_path / "Dockerfile"
        dockerfile_path.write_text(dockerfile, encoding="utf-8")

        cmd = [
            "podman",
            "--root", "/scratch0/ihbas/.containers/storage",
            "--runroot", "/scratch0/ihbas/.containers/tmp",
            "--storage-driver", "overlay",
            "build",
            "-t", image_name,
            str(tmpdir_path)
        ]
        print(f"📦 Building Podman image: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            raise RuntimeError(
                "Failed to build Podman image:\n"
                f"EXIT: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
            )
        else:
            print("✅ Podman image built successfully.")


def run_tests_in_podman(
    repo_path: Path,
    tests: List[str],
    image_name: str = "verifier-swebench:latest",
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Run pytest inside a Podman container over the given repo.

    Parameters
    ----------
    repo_path : Path
        Local path to the patched repository.
    tests : List[str]
        List of pytest node ids (e.g. 'tests/test_foo.py::test_bar').
        If empty, runs 'pytest -q' over the whole suite.
    image_name : str
        Podman image to use.
    extra_env : Dict[str,str], optional
        Extra env vars to pass into the container.

    Returns
    -------
    dict with keys: 'returncode', 'stdout', 'stderr'
    """
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    env_args: List[str] = []
    merged_env = {"PYTHONPATH": "/workspace"}
    if extra_env:
        merged_env.update(extra_env)

    for k, v in merged_env.items():
        env_args.extend(["-e", f"{k}={v}"])

    # If no specific tests are given, run full suite
    test_args = tests or []
    cmd = [
        "podman",
        "--root", "/scratch0/ihbas/.containers/storage",
        "--runroot", "/scratch0/ihbas/.containers/tmp",
        "--storage-driver", "overlay",
        "run",
        "--rm",
        "-v",
        f"{str(repo_path)}:/workspace:Z",  # :Z for SELinux-friendly relabel
        "-w",
        "/workspace",
        *env_args,
        image_name,
        "pytest",
        "-q",
        *test_args,
    ]

    print(f"🧪 Running tests in Podman:\n  {' '.join(cmd)}\n")
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
    image_name: str = "verifier-swebench:latest",
    dataset_source: str = "princeton-nlp/SWE-bench_Verified",
    hf_mode: bool = True,
    split: str = "test",
    repos_root: Path | str | None = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate model patches on SWE-bench-style tasks inside a Podman container.

    This function is conceptually similar to SWE-bench's `run_evaluation`,
    but implemented entirely inside the verifier-harness repository.

    Parameters
    ----------
    predictions : list of dict
        Each dict must contain at least:
          - 'instance_id'
          - 'model_name_or_path'
          - 'model_patch' (unified diff string)
    image_name : str
        Podman image tag to run tests in.
    dataset_source : str
        Source passed to DatasetLoader; default is HF SWE-bench Verified.
    hf_mode : bool
        Whether DatasetLoader should use HuggingFace mode.
    split : str
        Dataset split (e.g. 'test').
    repos_root : Path or str, optional
        Where to store cloned repos. Defaults to PROJECT_ROOT / "repos_temp".

    Returns
    -------
    List[Dict[str, Any]]
        Per-prediction results, including pass/fail and logs.
    """
    if repos_root is None:
        repos_root = PROJECT_ROOT / "repos_temp"
    repos_root = Path(repos_root)
    repos_root.mkdir(parents=True, exist_ok=True)

    # Ensure Podman image exists (idempotent; Podman will reuse cache)
    build_podman_image(image_name=image_name)

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
        fail_to_pass: List[str] = metadata.get("FAIL_TO_PASS", []) or []
        pass_to_pass: List[str] = metadata.get("PASS_TO_PASS", []) or []

        # Combined patch = test patch (T) + model patch (δ̂)
        # This approximates SWE-bench's sequence "apply T, then apply δ̂".
        combined_patch_parts: List[str] = []
        if test_patch_text.strip():
            combined_patch_parts.append(test_patch_text.rstrip() + "\n")
        combined_patch_parts.append(model_patch)
        combined_patch = "\n".join(combined_patch_parts)

        # Prepare sample for PatchLoader (override 'patch' with combined patch)
        patched_sample = dict(sample)
        patched_sample["patch"] = combined_patch

        patcher = PatchLoader(
            patched_sample,
            repos_root=repos_root,
        )

        # Clean up any stale repos from previous runs
        try:
            patcher.cleanup_old_repos()
        except Exception as e:
            print(f"⚠️  Warning: failed to cleanup old repos: {e}")

        # Clone + apply combined patch
        try:
            patch_result = patcher.load_and_apply()
        except PatchApplicationError as e:
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "patch_application_failed",
                    "error": f"PatchApplicationError: {e}",
                }
            )
            continue
        except Exception as e:  # noqa: BLE001
            results.append(
                {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "status": "patch_application_failed",
                    "error": f"Unexpected error applying patch: {e}",
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

        # Tests according to SWE-bench completion definition
        tests_to_run = list(dict.fromkeys(fail_to_pass + pass_to_pass))

        # Run tests in Podman
        test_result = run_tests_in_podman(
            repo_path=repo_path,
            tests=tests_to_run,
            image_name=image_name,
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
    - Evaluates a single sympy patch inside a Podman container.
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
            image_name="verifier-swebench:latest",
            dataset_source="princeton-nlp/SWE-bench_Verified",
            hf_mode=True,
            split="test",
        )
    except Exception as e:  # noqa: BLE001
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)

    print("\n📊 Evaluation results:")
    print(json.dumps(eval_results, indent=2))
