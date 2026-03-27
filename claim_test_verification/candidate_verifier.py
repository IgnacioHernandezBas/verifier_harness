"""
Candidate Patch Verification
=============================
Reusable logic for testing candidate patches against discriminative claim tests.

Takes VALID tests from the agentic closed loop and runs them against candidate
patches from SWE-bench experiments (instead of the gold patch).

Interpretation of results:
  BUG=FAIL, CANDIDATE=PASS  -> VALID: candidate is semantically correct
  BUG=FAIL, CANDIDATE=FAIL  -> OVERCONSTRAINED: candidate may be a false positive
  BUG=PASS, CANDIDATE=PASS  -> NON_DISCRIMINATIVE: test doesn't distinguish
  BUG=PASS, CANDIDATE=FAIL  -> INVERTED: unexpected behavior
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from claim_test_verification.claim_test_verifier import verify_instance

logger = logging.getLogger(__name__)

# Default paths (can be overridden)
HARNESS_ROOT = Path("/fs/nexus-scratch/ihbas/verifier_harness")
EXPERIMENTS_LITE = Path(
    "/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite"
)
TESTS_OUT_ROOT = HARNESS_ROOT / "claim_test_generation" / "tests_out"
STATE_DIR = HARNESS_ROOT / "agentic_closed_loop" / "state"


def load_sample_from_state(
    instance_id: str,
    claim_id: str,
    state_dir: Optional[Path] = None,
) -> dict:
    """Load the sample dict from the agentic loop state file."""
    state_dir = state_dir or STATE_DIR
    state_file = state_dir / f"{instance_id}_{claim_id}.json"
    if not state_file.exists():
        raise FileNotFoundError(f"State file not found: {state_file}")
    with open(state_file) as f:
        state = json.load(f)
    return state["sample"]


def get_resolved_experiments(
    instance_id: str,
    experiments_dir: Optional[Path] = None,
) -> List[Tuple[str, str]]:
    """
    Find all experiments where instance_id is 'resolved' AND has a .diff file.
    Returns list of (experiment_name, diff_path).
    """
    experiments_dir = experiments_dir or EXPERIMENTS_LITE
    candidates = []
    for exp_dir in sorted(experiments_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        results_file = exp_dir / "results" / "results.json"
        if not results_file.exists():
            continue
        with open(results_file) as f:
            data = json.load(f)
        if instance_id not in data.get("resolved", []):
            continue
        diff_path = exp_dir / "logs" / instance_id / "patch.diff"
        if diff_path.exists() and diff_path.read_text().strip():
            candidates.append((exp_dir.name, str(diff_path)))
    return candidates


def get_failed_experiments(
    instance_id: str,
    experiments_dir: Optional[Path] = None,
) -> List[Tuple[str, str]]:
    """
    Find experiments where instance_id has a .diff but is NOT resolved.
    These are patches that fail SWE-bench tests.
    """
    experiments_dir = experiments_dir or EXPERIMENTS_LITE
    candidates = []
    for exp_dir in sorted(experiments_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        results_file = exp_dir / "results" / "results.json"
        if not results_file.exists():
            continue
        with open(results_file) as f:
            data = json.load(f)
        resolved = data.get("resolved", [])
        no_gen = data.get("no_generation", [])
        if instance_id in resolved or instance_id in no_gen:
            continue
        diff_path = exp_dir / "logs" / instance_id / "patch.diff"
        if diff_path.exists() and diff_path.read_text().strip():
            candidates.append((exp_dir.name, str(diff_path)))
    return candidates


def normalize_patch(diff_text: str) -> str:
    """
    Normalize a candidate diff for git apply compatibility.
    Preserves the single-space prefix on empty context lines.
    """
    text = diff_text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.rstrip("\n") + "\n"
    return text


def verify_candidate_patch(
    sample: dict,
    candidate_diff: str,
    claim_tests_root: Path,
    timeout_s: int = 300,
) -> dict:
    """
    Run verify_instance with a candidate patch instead of the gold patch.
    The BUG version remains unchanged (no patch applied).
    The 'GOLD' version will have the candidate patch applied instead.
    """
    modified_sample = copy.deepcopy(sample)
    modified_sample["patch"] = normalize_patch(candidate_diff)
    return verify_instance(
        modified_sample,
        claim_tests_root=claim_tests_root,
        use_container=True,
        timeout_s=timeout_s,
    )


def list_available_state_instances(
    state_dir: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """List all instance/claim combinations available in the state directory."""
    state_dir = state_dir or STATE_DIR
    if not state_dir.exists():
        return []
    instances = []
    for f in sorted(state_dir.glob("*.json")):
        name = f.stem
        # Parse instance_id and claim_id from filename like "django__django-11964_C1"
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].startswith("C"):
            instances.append({
                "instance_id": parts[0],
                "claim_id": parts[1],
                "state_file": str(f),
            })
    return instances


def get_cached_instance_ids(cache_dir: Optional[Path] = None) -> List[str]:
    """Return instance IDs that have a cached Singularity .sif image."""
    if cache_dir is None:
        # Try known cache paths
        candidates = [
            Path("/fs/nexus-scratch/ihbas/.cache/swebench_singularity"),
            Path.home() / ".cache" / "swebench_singularity",
        ]
        for p in candidates:
            if p.exists():
                cache_dir = p
                break
    if cache_dir is None or not cache_dir.exists():
        return []
    return sorted(f.stem for f in cache_dir.rglob("*.sif") if f.is_file())


def get_gold_valid_instances(
    results_root: Optional[Path] = None,
) -> List[Dict[str, str]]:
    """
    Scan agentic loop results and return instances that have at least one
    VALID gold-patch result (status=success, classification=VALID).

    Returns list of dicts with: instance_id, claim_id, tests_model, claims_model, summary_file
    """
    results_root = results_root or (HARNESS_ROOT / "agentic_closed_loop" / "results")
    if not results_root.exists():
        return []

    valid_instances = []
    for summary_file in results_root.rglob("*_summary.json"):
        try:
            with open(summary_file) as f:
                data = json.load(f)
            if data.get("status") != "success":
                continue
            final = data.get("final_result", {})
            if final.get("classification") != "VALID":
                continue
            valid_instances.append({
                "instance_id": data.get("instance_id", ""),
                "claim_id": data.get("claim_id", ""),
                "tests_model": data.get("models", {}).get("tests_model", ""),
                "claims_model": data.get("models", {}).get("claims_model", ""),
                "summary_file": str(summary_file),
            })
        except Exception:
            continue

    return valid_instances


def get_eligible_instances(
    results_root: Optional[Path] = None,
    cache_dir: Optional[Path] = None,
) -> List[Dict]:
    """
    Return instances that are both cached (have .sif) AND have at least one
    VALID gold-patch result. Groups by instance_id.
    """
    cached_ids = set(get_cached_instance_ids(cache_dir))
    valid = get_gold_valid_instances(results_root)

    # Filter to only cached + group by instance_id
    by_instance: Dict[str, Dict] = {}
    for v in valid:
        iid = v["instance_id"]
        if iid not in cached_ids:
            continue
        if iid not in by_instance:
            by_instance[iid] = {
                "instance_id": iid,
                "valid_claims": [],
            }
        by_instance[iid]["valid_claims"].append({
            "claim_id": v["claim_id"],
            "tests_model": v["tests_model"],
            "claims_model": v["claims_model"],
        })

    return sorted(by_instance.values(), key=lambda x: x["instance_id"])


def list_available_test_models(
    tests_out_root: Optional[Path] = None,
) -> List[str]:
    """List model directories available in tests_out."""
    tests_out_root = tests_out_root or TESTS_OUT_ROOT
    if not tests_out_root.exists():
        return []
    return sorted(
        d.name for d in tests_out_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def run_candidate_verification(
    instance_id: str,
    claim_id: str = "C1",
    tests_model: str = "Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
    include_failed: bool = True,
    max_candidates: Optional[int] = None,
    timeout_s: int = 300,
    state_dir: Optional[Path] = None,
    tests_out_root: Optional[Path] = None,
    experiments_dir: Optional[Path] = None,
    progress_callback=None,
) -> Dict:
    """
    Run candidate patch verification for a single instance/claim.

    Parameters
    ----------
    instance_id : str
        SWE-bench instance ID.
    claim_id : str
        Claim identifier (e.g. "C1").
    tests_model : str
        Which model's generated tests to use.
    include_failed : bool
        Also test patches that failed SWE-bench evaluation.
    max_candidates : int, optional
        Limit number of candidate patches to test.
    timeout_s : int
        Per-test timeout in seconds.
    progress_callback : callable, optional
        Called with (message: str) for progress updates.

    Returns
    -------
    dict with keys: instance_id, claim_id, tests_model, timestamp,
                    gold_result, candidates, summary
    """
    tests_out_root = tests_out_root or TESTS_OUT_ROOT

    def _progress(msg):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    # 1. Load sample from state
    _progress(f"Loading sample for {instance_id}/{claim_id}")
    gold_sample = load_sample_from_state(instance_id, claim_id, state_dir)
    gold_patch = gold_sample["patch"]

    # 2. Set up claim tests root
    claim_tests_root = tests_out_root / tests_model
    instance_test_dir = claim_tests_root / instance_id
    if not instance_test_dir.exists():
        return {
            "instance_id": instance_id,
            "claim_id": claim_id,
            "tests_model": tests_model,
            "error": f"No tests found at {instance_test_dir}",
        }

    test_files = list(instance_test_dir.glob("*test_claim_*.py"))
    _progress(f"Found {len(test_files)} claim test files")

    # 3. Collect candidates
    resolved = get_resolved_experiments(instance_id, experiments_dir)
    _progress(f"Found {len(resolved)} resolved experiments with diffs")

    failed = []
    if include_failed:
        failed = get_failed_experiments(instance_id, experiments_dir)
        _progress(f"Found {len(failed)} failed experiments with diffs")

    candidates_list = [(name, path, "resolved") for name, path in resolved]
    candidates_list += [(name, path, "failed") for name, path in failed]

    if max_candidates:
        candidates_list = candidates_list[:max_candidates]

    _progress(f"Will test {len(candidates_list)} candidate patches")

    # 4. Run gold patch as baseline
    _progress("Running GOLD patch as baseline...")
    gold_result = verify_candidate_patch(
        gold_sample, gold_patch, claim_tests_root, timeout_s
    )
    gold_classification = "N/A"
    if gold_result.get("tests"):
        gold_classification = gold_result["tests"][0]["classification"]["label"]
    _progress(f"Gold patch result: {gold_classification}")

    all_results = []
    all_results.append({
        "experiment": "GOLD_PATCH",
        "swebench_status": "gold",
        "patch_size": len(gold_patch),
        "semantic_result": gold_classification,
        "details": gold_result.get("summary", {}),
    })

    # 5. Run each candidate
    for i, (exp_name, diff_path, swe_status) in enumerate(candidates_list, 1):
        _progress(f"[{i}/{len(candidates_list)}] Testing {exp_name} ({swe_status})...")
        candidate_diff = Path(diff_path).read_text()

        result = verify_candidate_patch(
            gold_sample, candidate_diff, claim_tests_root, timeout_s
        )

        classification = "ERROR"
        if result.get("tests"):
            classification = result["tests"][0]["classification"]["label"]
        elif result.get("error"):
            err = result["error"]
            if "Patch failed" in err or "Failed to apply" in err:
                classification = "PATCH_APPLY_FAILED"
            else:
                classification = f"ERROR: {err[:100]}"

        _progress(f"  {exp_name} | swebench={swe_status} | semantic={classification}")

        all_results.append({
            "experiment": exp_name,
            "swebench_status": swe_status,
            "patch_size": len(candidate_diff.strip()),
            "semantic_result": classification,
            "details": result.get("summary", {}),
        })

    # 6. Build summary
    from collections import Counter

    resolved_results = [r for r in all_results if r["swebench_status"] == "resolved"]
    failed_results = [r for r in all_results if r["swebench_status"] == "failed"]

    resolved_cls = Counter(r["semantic_result"] for r in resolved_results)
    failed_cls = Counter(r["semantic_result"] for r in failed_results)

    sem_valid_resolved = sum(
        1 for r in resolved_results if r["semantic_result"] == "VALID"
    )
    false_positives = [
        r for r in resolved_results
        if r["semantic_result"] not in ("VALID", "PATCH_APPLY_FAILED")
    ]

    output = {
        "instance_id": instance_id,
        "claim_id": claim_id,
        "tests_model": tests_model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gold_patch_size": len(gold_patch),
        "gold_classification": gold_classification,
        "total_candidates": len(candidates_list),
        "results": all_results,
        "summary": {
            "resolved_count": len(resolved_results),
            "resolved_classifications": dict(resolved_cls),
            "resolved_semantically_valid": sem_valid_resolved,
            "false_positives": len(false_positives),
            "false_positive_experiments": [
                fp["experiment"] for fp in false_positives
            ],
            "failed_count": len(failed_results),
            "failed_classifications": dict(failed_cls),
        },
    }

    return output
