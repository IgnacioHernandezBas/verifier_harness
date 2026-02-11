"""Headless verification of claim-tests (BUG vs GOLD) using Singularity."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from swebench_integration import PatchLoader
from swebench_singularity import Config, SingularityBuilder

from verifier.dynamic_analyzers import test_patch_singularity

logger = logging.getLogger(__name__)

STDIO_LIMIT = 10_000

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_ERROR = "ERROR"
STATUS_TIMEOUT = "TIMEOUT"

LABEL_VALID = "VALID"
LABEL_NON_DISCRIMINATIVE = "NON_DISCRIMINATIVE"
LABEL_OVERCONSTRAINED = "OVERCONSTRAINED"
LABEL_INVERTED = "INVERTED"
LABEL_UNRESOLVED = "UNRESOLVED"


def verify_instance(
    sample: Dict,
    claim_tests_root: Path | str,
    use_container: bool = True,
    timeout_s: int = 300,
    max_claims: Optional[int] = None,
) -> Dict:
    """
    Verify claim-tests for a single SWE-bench sample.

    Returns a dict with BUG vs GOLD execution details, classification counts, and CVR.
    """

    claim_tests_root = Path(claim_tests_root)
    metadata = sample.get("metadata", {}) or {}
    instance_id = metadata.get("instance_id") or sample.get("instance_id")

    result: Dict[str, object] = {
        "instance_id": instance_id,
        "repo": sample.get("repo"),
        "base_commit": sample.get("base_commit"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "claim_tests_root": str(claim_tests_root),
        "tests": [],
        "summary": {},
        "success": False,
    }

    if not instance_id:
        result["error"] = "Sample missing metadata.instance_id"
        return result

    if not claim_tests_root.exists():
        result["error"] = f"Claim-tests root does not exist: {claim_tests_root}"
        return result

    if not use_container:
        result["error"] = "Singularity execution is required for SWE-bench parity."
        return result

    claim_dir = claim_tests_root / instance_id
    if not claim_dir.exists():
        result["skip_reason"] = f"No claim-tests found for {instance_id}"
        return result

    container_path = _build_or_get_container(instance_id)
    if not container_path:
        result["error"] = f"Unable to prepare Singularity container for {instance_id}"
        return result
    result["container_path"] = str(container_path)

    temp_root = Path(tempfile.mkdtemp(prefix=f"claim_verify_{instance_id}_"))

    try:
        bug_loader = PatchLoader(sample, repos_root=temp_root / "bug")
        gold_loader = PatchLoader(sample, repos_root=temp_root / "gold")

        bug_repo = Path(bug_loader.clone_repository())
        gold_repo = Path(gold_loader.clone_repository())

        _apply_test_patch_if_needed(bug_loader, metadata)

        try:
            gold_loader.apply_patch()
        except Exception as exc:  # pragma: no cover - just defensive
            result["error"] = f"Failed to apply GOLD patch: {exc}"
            return result

        _apply_test_patch_if_needed(gold_loader, metadata)

        result["bug_repo_path"] = str(bug_repo)
        result["gold_repo_path"] = str(gold_repo)

        _copy_claim_tests(instance_id, claim_tests_root, bug_repo)
        _copy_claim_tests(instance_id, claim_tests_root, gold_repo)

        claim_files = discover_claim_test_files(bug_repo, instance_id)
        if not claim_files:
            result["skip_reason"] = "No claim-test files discovered after sync."
            return result

        if max_claims is not None:
            claim_files = claim_files[: max(0, max_claims)]

        if not claim_files:
            result["skip_reason"] = "max_claims_per_instance limited tests to zero."
            return result

        _install_dependencies(bug_repo, container_path)
        _install_dependencies(gold_repo, container_path)

        tests_output: List[Dict[str, object]] = []
        label_counts: Counter = Counter()

        for rel_path in claim_files:
            bug_run = run_single_claim_test_in_singularity(
                bug_repo, container_path, rel_path, timeout_s
            )
            gold_run = run_single_claim_test_in_singularity(
                gold_repo, container_path, rel_path, timeout_s
            )

            label, reason = classify(bug_run["status"], gold_run["status"])
            label_counts[label] += 1

            tests_output.append(
                {
                    "test_path": rel_path,
                    "bug": bug_run,
                    "gold": gold_run,
                    "classification": {"label": label, "reason": reason},
                }
            )

        total = len(tests_output)
        valid = label_counts[LABEL_VALID]
        summary = {
            "total_claim_tests": total,
            "label_counts": dict(label_counts),
            "valid": valid,
            "cvr": (valid / total) if total else 0.0,
        }

        result["tests"] = tests_output
        result["summary"] = summary
        result["success"] = total > 0
        return result

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Claim-test verification failed for %s", instance_id)
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        return result
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def discover_claim_test_files(repo_path: Path, instance_id: str) -> List[str]:
    """Return sorted relative claim-test paths for a repository."""
    claim_dir = Path(repo_path) / "claim_tests" / instance_id
    if not claim_dir.exists():
        return []

    return [
        path.relative_to(repo_path).as_posix()
        for path in sorted(claim_dir.rglob("*.py"))
        if path.is_file()
    ]


def run_single_claim_test_in_singularity(
    repo_path: Path,
    container_path: Path,
    rel_test_path: str,
    timeout_s: int,
) -> Dict[str, object]:
    """Execute a single claim-test file via pytest inside Singularity with timeout."""

    queue: "Queue[Dict[str, object]]" = Queue()
    start = time.time()

    worker = Process(
        target=_singularity_worker,
        args=(queue, str(repo_path), str(container_path), rel_test_path),
    )
    worker.start()
    worker.join(timeout_s)

    if worker.is_alive():
        worker.terminate()
        worker.join()
        return {
            "status": STATUS_TIMEOUT,
            "returncode": None,
            "stdout": "",
            "stderr": f"Timed out after {timeout_s}s",
            "duration_s": time.time() - start,
        }

    duration = time.time() - start
    if queue.empty():
        return {
            "status": STATUS_ERROR,
            "returncode": None,
            "stdout": "",
            "stderr": "Singularity worker produced no output",
            "duration_s": duration,
        }

    payload = queue.get()
    queue.close()

    if not payload.get("ok"):
        return {
            "status": STATUS_ERROR,
            "returncode": None,
            "stdout": "",
            "stderr": payload.get("error", "Unknown worker failure"),
            "duration_s": duration,
        }

    sing_result = payload["result"]
    returncode = sing_result.get("returncode")
    status = _status_from_returncode(returncode)

    return {
        "status": status,
        "returncode": returncode,
        "stdout": _truncate(sing_result.get("stdout", "")),
        "stderr": _truncate(sing_result.get("stderr", "")),
        "duration_s": duration,
    }


def classify(bug_status: str, gold_status: str) -> Tuple[str, str]:
    """Classify BUG vs GOLD outcomes into a label + explanation."""
    if STATUS_TIMEOUT in (bug_status, gold_status) or STATUS_ERROR in (
        bug_status,
        gold_status,
    ):
        return LABEL_UNRESOLVED, f"Non-deterministic: BUG={bug_status}, GOLD={gold_status}"

    if bug_status == STATUS_FAIL and gold_status == STATUS_PASS:
        return LABEL_VALID, "Bug reproduced (BUG=FAIL) and fixed (GOLD=PASS)."

    if bug_status == STATUS_PASS and gold_status == STATUS_PASS:
        return LABEL_NON_DISCRIMINATIVE, "Claim-test passes on both variants."

    if bug_status == STATUS_FAIL and gold_status == STATUS_FAIL:
        return LABEL_OVERCONSTRAINED, "Claim-test fails on both variants."

    if bug_status == STATUS_PASS and gold_status == STATUS_FAIL:
        return LABEL_INVERTED, "Regression introduced: GOLD fails while BUG passes."

    return LABEL_UNRESOLVED, f"Unhandled combination BUG={bug_status}, GOLD={gold_status}"


def _singularity_worker(
    queue: "Queue[Dict[str, object]]",
    repo_path: str,
    container_path: str,
    rel_test_path: str,
) -> None:
    try:
        result = test_patch_singularity.run_tests_in_singularity(
            Path(repo_path),
            tests=[rel_test_path],
            image_path=container_path,
            collect_coverage=False,
            verbose=True,  # Enable verbose mode to get full assertion details for agent learning
            test_framework_hint="pytest",
        )
        queue.put({"ok": True, "result": result})
    except Exception as exc:  # pragma: no cover - defensive
        queue.put({"ok": False, "error": str(exc)})


def _status_from_returncode(returncode: Optional[int]) -> str:
    if returncode == 0:
        return STATUS_PASS
    if returncode == 1:
        return STATUS_FAIL
    if returncode is None:
        return STATUS_ERROR
    return STATUS_ERROR


def _truncate(text: str) -> str:
    if not text:
        return ""
    if len(text) <= STDIO_LIMIT:
        return text
    return text[-STDIO_LIMIT:]


def _apply_test_patch_if_needed(loader: PatchLoader, metadata: Dict) -> None:
    test_patch = metadata.get("test_patch")
    if not test_patch or not str(test_patch).strip():
        return
    loader.apply_additional_patch(str(test_patch))


def _copy_claim_tests(instance_id: str, claim_tests_root: Path, repo_path: Path) -> bool:
    src_dir = Path(claim_tests_root) / instance_id
    if not src_dir.exists():
        return False

    dest_dir = Path(repo_path) / "claim_tests" / instance_id
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dest_dir)
    return True


def _install_dependencies(repo_path: Path, container_path: Path) -> None:
    install_result = test_patch_singularity.install_package_in_singularity(
        repo_path=repo_path,
        image_path=str(container_path),
    )
    if install_result.get("returncode", 0) != 0:
        logger.warning(
            "Dependency installation reported returncode=%s for %s",
            install_result.get("returncode"),
            repo_path,
        )


def _build_or_get_container(instance_id: str) -> Optional[Path]:
    config = Config()
    builder = SingularityBuilder(config)
    build_result = builder.build_instance(
        instance_id=instance_id,
        force_rebuild=False,
        check_docker_exists=False,
    )
    if build_result.success and build_result.sif_path:
        return build_result.sif_path

    logger.error(
        "Failed to get Singularity container for %s: %s",
        instance_id,
        build_result.error_message,
    )
    return None
