#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from claim_test_generation.claim_test_generator import (
    VLLMClient,
    generate_pytest_for_claim,
)
from claim_test_generation.generate_claim_tests import _sanitize
from claim_test_verification import verify_instance
from common.model_paths import ModelPaths, MultiModelPaths


def parse_args() -> argparse.Namespace:
    default_endpoint = os.getenv("CLAIM_LLM_ENDPOINT", "http://127.0.0.1:8000/v1")
    default_model = os.getenv("CLAIM_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ")
    default_api_key = os.getenv("CLAIM_LLM_API_KEY")

    ap = argparse.ArgumentParser(
        description="Prototype closed-loop generation/verification for a single claim.",
    )
    ap.add_argument("--instance_id", required=True, help="Target SWE-bench instance id.")
    ap.add_argument("--claim_id", default="C1", help="Claim identifier (default: C1).")
    ap.add_argument(
        "--claims_dir",
        help="Directory with claim JSON files (overrides --claims_model).",
    )
    ap.add_argument(
        "--claims_model",
        help="Model used for claim extraction (determines claims input directory).",
    )
    ap.add_argument(
        "--instances_file",
        default="claim_extraction/instances.json",
        help="File containing prepared instance metadata.",
    )
    ap.add_argument(
        "--tests_root",
        help="Directory where test files are written/read (overrides --model).",
    )
    ap.add_argument(
        "--claim_tests_root",
        help="Root copied into repos during verification (overrides --model).",
    )
    ap.add_argument("--max_attempts", type=int, default=3)
    ap.add_argument("--timeout_s", type=int, default=300)
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--endpoint", default=default_endpoint)
    ap.add_argument("--model", default=default_model, help="Model for test generation.")
    ap.add_argument("--api_key", default=default_api_key)
    ap.add_argument(
        "--log_path",
        default=None,
        help="Optional explicit path for attempt log JSON. Defaults to tests dir.",
    )
    ap.add_argument(
        "--use_model_subdirs",
        action="store_true",
        default=True,
        help="Use model-specific subdirectories (default: True).",
    )
    ap.add_argument(
        "--no_model_subdirs",
        action="store_false",
        dest="use_model_subdirs",
        help="Use legacy flat directory structure.",
    )
    return ap.parse_args()


def load_instance_sample(path: Path, instance_id: str) -> Dict[str, Any]:
    data = json.loads(path.read_text())
    record = next(
        (item for item in data if item.get("instance_id") == instance_id), None
    )
    if not record:
        raise SystemExit(f"Instance {instance_id} not found in {path}")
    sample: Dict[str, Any] = {
        "repo": record["repo"],
        "base_commit": record["base_commit"],
        "patch": record.get("patch"),
        "test_patch": record.get("test_patch"),
        "metadata": {"instance_id": record["instance_id"]},
        "instance_id": record["instance_id"],
    }
    return sample


def load_claim(claims_dir: Path, instance_id: str, claim_id: str) -> Dict[str, Any]:
    claim_file = claims_dir / f"{instance_id}.json"
    data = json.loads(claim_file.read_text())
    claim = next(
        (item for item in data.get("claims", []) if item.get("claim_id") == claim_id),
        None,
    )
    if not claim:
        raise SystemExit(f"Claim {claim_id} missing from {claim_file}")
    return claim


def result_success(result: Dict[str, Any]) -> bool:
    summary = result.get("summary") or {}
    return bool(summary.get("valid"))


def extract_failure_snippet(payload: Dict[str, Any]) -> str:
    stdout = (payload.get("stdout") or "").strip()
    stderr = (payload.get("stderr") or "").strip()
    text = stdout or stderr
    if not text:
        return "no stdout/stderr captured"
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("="):
            return line[:240]
    return text.splitlines()[0][:240]


def build_feedback_from_result(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return f"Verifier error: {result['error']}"
    tests = result.get("tests") or []
    if not tests:
        return "No tests ran; claim dir empty or skipped."
    lines: List[str] = []
    for test in tests:
        path = test.get("test_path")
        classification = test.get("classification", {})
        bug = test.get("bug", {})
        gold = test.get("gold", {})
        lines.append(
            f"{path}: label={classification.get('label')} (reason={classification.get('reason')})"
        )
        lines.append(
            f"BUG={bug.get('status')} ⇒ {extract_failure_snippet(bug)}"
        )
        lines.append(
            f"GOLD={gold.get('status')} ⇒ {extract_failure_snippet(gold)}"
        )
    return "\n".join(lines)


def feedback_prompt(attempt: int, feedback: str) -> List[Dict[str, str]]:
    content = (
        f"Attempt {attempt} failed verification. "
        "Revise the pytest so it exercises the claim precisely and avoids the failure below:\n"
        f"{feedback}\n"
        "Do not skip the test. Prefer realistic fixtures that mirror the claim scenario."
    )
    return [{"role": "user", "content": content}]


def write_test_file(code: str, tests_dir: Path, instance_id: str, claim_id: str) -> Path:
    instance_slug = _sanitize(instance_id)
    claim_slug = _sanitize(claim_id)
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_path = tests_dir / f"{instance_slug}__test_claim_{claim_slug}.py"
    test_path.write_text(code, encoding="utf-8")
    return test_path


def main() -> None:
    args = parse_args()

    # Determine paths using ModelPaths or explicit directories
    if args.claims_dir and args.tests_root and args.claim_tests_root:
        # Legacy mode: explicit directories provided
        claims_dir = Path(args.claims_dir).resolve()
        tests_root = Path(args.tests_root).resolve()
        claim_tests_root = Path(args.claim_tests_root).resolve()
    else:
        # New mode: use ModelPaths
        if not args.claims_model:
            # If no claims_model specified, use the test generation model
            claims_model = args.model
        else:
            claims_model = args.claims_model

        paths = MultiModelPaths(
            claims_model=claims_model,
            tests_model=args.model,
            use_model_subdirs=args.use_model_subdirs,
        )
        claims_dir = paths.claims_dir()
        tests_root = paths.tests_root()
        claim_tests_root = paths.tests_root()

    instances_path = Path(args.instances_file).resolve()

    sample = load_instance_sample(instances_path, args.instance_id)
    claim = load_claim(claims_dir, args.instance_id, args.claim_id)

    client = VLLMClient(
        endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout_s,
        api_key=args.api_key,
    )

    tests_dir = tests_root / args.instance_id
    log_path = (
        Path(args.log_path).resolve()
        if args.log_path
        else tests_dir / f"{_sanitize(args.instance_id)}__closed_loop_log.json"
    )

    attempt_logs: List[Dict[str, Any]] = []
    success = False
    previous_feedback: Optional[str] = None

    for attempt in range(1, args.max_attempts + 1):
        extra_messages = (
            feedback_prompt(attempt, previous_feedback)
            if previous_feedback
            else None
        )
        code = generate_pytest_for_claim(
            claim=claim,
            repo=sample["repo"],
            instance_id=args.instance_id,
            client=client,
            extra_messages=extra_messages,
        )
        test_path = write_test_file(code, tests_dir, args.instance_id, args.claim_id)
        print(f"[attempt {attempt}] Wrote {test_path}")

        result = verify_instance(
            sample=sample,
            claim_tests_root=claim_tests_root,
            use_container=True,
            timeout_s=args.timeout_s,
            max_claims=1,
        )

        attempt_record = {
            "attempt": attempt,
            "test_path": str(test_path),
            "success": result_success(result),
            "result": result,
            "feedback_used": previous_feedback,
        }
        attempt_logs.append(attempt_record)

        if result_success(result):
            print(f"[attempt {attempt}] Found BUG≠GOLD signal 🎉")
            success = True
            break

        previous_feedback = build_feedback_from_result(result)
        print(f"[attempt {attempt}] Still failing:\n{previous_feedback}\n")

    log_path.write_text(
        json.dumps(
            {
                "instance_id": args.instance_id,
                "claim_id": args.claim_id,
                "success": success,
                "attempts": attempt_logs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if not success:
        raise SystemExit(
            f"Closed-loop exhausted {args.max_attempts} attempts without success. "
            f"See {log_path} for details."
        )


if __name__ == "__main__":
    main()
