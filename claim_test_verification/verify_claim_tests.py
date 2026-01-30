#!/usr/bin/env python3
"""
Headless claim-test verification CLI.

Example:
    python claim_test_verification/verify_claim_tests.py \\
        --limit 5 \\
        --claim_tests_root /fs/nexus-scratch/ihbas/verifier_harness/claim-tests \\
        --out_dir verification_out
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Dict

from swebench_integration import DatasetLoader

from claim_test_verification import verify_instance

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify generated claim-tests against SWE-bench BUG vs GOLD repos",
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench_Lite",
        help="Dataset identifier or local JSON path.",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split (HuggingFace mode only).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of samples to process.",
    )
    parser.add_argument(
        "--filter_repo",
        type=str,
        default=None,
        help="Filter samples by repository substring.",
    )
    parser.add_argument(
        "--claim_tests_root",
        type=Path,
        required=True,
        help="Root directory that contains per-instance claim-tests.",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        required=True,
        help="Directory where per-instance results + summary.json will be written.",
    )
    parser.add_argument(
        "--timeout_s",
        type=int,
        default=300,
        help="Per-claim-test timeout (seconds).",
    )
    parser.add_argument(
        "--max_claims_per_instance",
        type=int,
        default=None,
        help="Optional cap on number of claim-test files to execute per instance.",
    )
    parser.add_argument(
        "--local_dataset",
        action="store_true",
        help="Treat --dataset as a local JSON file instead of a HuggingFace dataset.",
    )

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s - %(message)s",
    )
    args = parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    loader = DatasetLoader(
        source=args.dataset,
        split=args.split,
        hf_mode=not args.local_dataset,
    )

    summary_label_counts: Counter = Counter()
    total_claims = 0
    total_valid = 0
    processed = 0
    completed = 0
    skipped = 0
    errors = 0

    for sample in loader.iter_samples(limit=args.limit, filter_repo=args.filter_repo):
        processed += 1
        instance_id = sample.get("metadata", {}).get("instance_id") or f"sample_{processed}"
        logger.info("Processing %s", instance_id)

        claim_dir = args.claim_tests_root / instance_id
        if not claim_dir.exists():
            skipped += 1
            logger.info(
                "Skipping %s: claim-tests not found at %s",
                instance_id,
                claim_dir,
            )
            continue

        instance_result = verify_instance(
            sample=sample,
            claim_tests_root=args.claim_tests_root,
            use_container=True,
            timeout_s=args.timeout_s,
            max_claims=args.max_claims_per_instance,
        )

        summary = instance_result.get("summary", {}) or {}
        label_counts: Dict[str, int] = summary.get("label_counts", {})
        summary_label_counts.update(label_counts)
        total_claims += summary.get("total_claim_tests", 0) or 0
        total_valid += summary.get("valid", 0) or 0

        instance_dir = out_dir / instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)
        result_path = instance_dir / "results.json"
        result_path.write_text(json.dumps(instance_result, indent=2))
        logger.info("Saved results to %s", result_path)

        if instance_result.get("success"):
            completed += 1
        elif instance_result.get("skip_reason"):
            skipped += 1
            logger.info(
                "Skipped %s: %s",
                instance_id,
                instance_result.get("skip_reason"),
            )
        elif instance_result.get("error"):
            errors += 1
            logger.error(
                "Error verifying %s: %s",
                instance_id,
                instance_result.get("error"),
            )

    cvr = (total_valid / total_claims) if total_claims else 0.0
    summary_payload = {
        "dataset": args.dataset,
        "split": args.split,
        "limit": args.limit,
        "processed_instances": processed,
        "completed_instances": completed,
        "skipped_instances": skipped,
        "error_instances": errors,
        "total_claim_tests": total_claims,
        "valid_claim_tests": total_valid,
        "cvr": cvr,
        "label_totals": dict(summary_label_counts),
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2))
    logger.info("Wrote summary to %s", summary_path)


if __name__ == "__main__":
    main()
