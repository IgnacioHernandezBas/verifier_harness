#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from claim_test_generation.claim_test_generator import VLLMClient

from .loop import AgenticClosedLoop, LoopConfig


def parse_args() -> argparse.Namespace:
    default_endpoint = os.getenv("CLAIM_LLM_ENDPOINT", "http://127.0.0.1:8000/v1")
    default_model = os.getenv("CLAIM_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ")
    default_api_key = os.getenv("CLAIM_LLM_API_KEY")

    ap = argparse.ArgumentParser(
        description="Agentic closed-loop claim-test generation prototype.",
    )
    ap.add_argument("--instance_id", required=True)
    ap.add_argument("--claim_id", default="C1")
    ap.add_argument(
        "--claims_dir",
        default="claim_extraction/claims_out",
        help="Directory with claim JSON files.",
    )
    ap.add_argument(
        "--instances_file",
        default="claim_extraction/instances.json",
        help="Prepared instances file used for claim extraction.",
    )
    ap.add_argument(
        "--tests_root",
        default="claim_test_generation/tests_out",
        help="Directory where generated tests will be written.",
    )
    ap.add_argument(
        "--claim_tests_root",
        default="claim_test_generation/tests_out",
        help="Directory synced into repos for verification.",
    )
    ap.add_argument("--max_attempts", type=int, default=3)
    ap.add_argument("--timeout_s", type=int, default=300)
    ap.add_argument("--endpoint", default=default_endpoint)
    ap.add_argument("--model", default=default_model)
    ap.add_argument("--api_key", default=default_api_key)
    ap.add_argument("--log_path", default=None, help="Optional JSON log output path.")
    return ap.parse_args()


def load_instance(instances_path: Path, instance_id: str) -> Dict[str, Any]:
    data = json.loads(instances_path.read_text())
    record = next((item for item in data if item.get("instance_id") == instance_id), None)
    if not record:
        raise SystemExit(f"Instance {instance_id} not found in {instances_path}")
    sample: Dict[str, Any] = {
        "repo": record["repo"],
        "base_commit": record["base_commit"],
        "patch": record.get("patch"),
        "test_patch": record.get("test_patch"),
        "metadata": {"instance_id": record["instance_id"]},
        "instance_id": record["instance_id"],
    }
    return sample


def load_claim(
    claims_dir: Path, instance_id: str, claim_id: str
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    claim_file = claims_dir / f"{instance_id}.json"
    if not claim_file.exists():
        raise SystemExit(f"Claim file {claim_file} not found")
    data = json.loads(claim_file.read_text())
    claim = next(
        (item for item in data.get("claims", []) if item.get("claim_id") == claim_id),
        None,
    )
    if not claim:
        raise SystemExit(f"Claim {claim_id} missing from {claim_file}")
    return claim, data.get("issue_context")


def main() -> None:
    args = parse_args()
    claims_dir = Path(args.claims_dir).resolve()
    instances_path = Path(args.instances_file).resolve()
    tests_root = Path(args.tests_root).resolve()
    claim_tests_root = Path(args.claim_tests_root).resolve()
    log_path = Path(args.log_path).resolve() if args.log_path else None

    sample = load_instance(instances_path, args.instance_id)
    claim, issue_context = load_claim(claims_dir, args.instance_id, args.claim_id)

    client = VLLMClient(
        endpoint=args.endpoint,
        model=args.model,
        temperature=0.1,
        max_tokens=2048,
        timeout_s=args.timeout_s,
        api_key=args.api_key,
    )

    config = LoopConfig(
        tests_root=tests_root,
        claim_tests_root=claim_tests_root,
        max_attempts=args.max_attempts,
        timeout_s=args.timeout_s,
        log_path=log_path
        or (tests_root / args.instance_id / f"{args.instance_id}__agentic_log.json"),
    )

    loop = AgenticClosedLoop(
        sample=sample,
        claim=claim,
        client=client,
        config=config,
        issue_context=issue_context,
    )
    payload = loop.run()
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
