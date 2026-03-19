#!/usr/bin/env python3
"""
Hybrid agentic loop runner that separates planning (host) from verification (container).

Usage:
  # Phase 1 (planning) - runs outside container in conda env
  python -m agentic_closed_loop.run_agentic_loop_hybrid \
    --phase plan \
    --instance_id astropy__astropy-7746 \
    --claim_id C1 \
    --state_file /tmp/agentic_state.json

  # Phase 2 (verification) - runs inside Singularity
  singularity exec verifier.sif python -m agentic_closed_loop.run_agentic_loop_hybrid \
    --phase verify \
    --state_file /tmp/agentic_state.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Lazy imports to avoid pulling in dependencies not available in container
# from claim_test_generation.claim_test_generator import VLLMClient
# from .context import (...)
# from .context_builder import enrich_claim_context
# from .loop import LoopConfig
# These are imported inside run_plan_phase() instead


def parse_args() -> argparse.Namespace:
    default_endpoint = os.getenv("CLAIM_LLM_ENDPOINT", "http://127.0.0.1:8000/v1")
    default_model = os.getenv("CLAIM_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ")
    default_api_key = os.getenv("CLAIM_LLM_API_KEY")

    ap = argparse.ArgumentParser(
        description="Hybrid agentic loop v2.0: separate planning (host) from verification (container) with multi-model support.",
    )
    ap.add_argument(
        "--phase",
        required=True,
        choices=["plan", "verify", "full"],
        help="Execution phase: 'plan' (context+generation), 'verify' (test execution), or 'full' (both)",
    )
    ap.add_argument(
        "--state_file",
        type=Path,
        required=True,
        help="JSON file for serializing state between phases",
    )
    ap.add_argument("--instance_id", help="Instance ID (required for plan phase)")
    ap.add_argument("--claim_id", default="C1", help="Claim ID")
    ap.add_argument(
        "--claims_dir",
        default="claim_extraction/claims_out",
        help="Directory with claim JSON files (legacy) or base directory for model-specific claims",
    )
    ap.add_argument(
        "--instances_file",
        default="claim_extraction/instances.json",
        help="Prepared instances file",
    )
    ap.add_argument(
        "--tests_root",
        default="claim_test_generation/tests_out",
        help="Directory where generated tests will be written (legacy) or base directory for model-specific tests",
    )
    ap.add_argument(
        "--claim_tests_root",
        default="claim_test_generation/tests_out",
        help="Directory synced into repos for verification",
    )
    ap.add_argument(
        "--repos_root",
        default="repos_temp_demo",
        help="Root directory containing checked-out repos for context gathering",
    )
    ap.add_argument("--max_attempts", type=int, default=3)
    ap.add_argument("--timeout_s", type=int, default=300)
    ap.add_argument("--endpoint", default=default_endpoint)
    ap.add_argument("--model", default=default_model)
    ap.add_argument("--api_key", default=default_api_key)
    ap.add_argument("--log_path", default=None, help="Optional JSON log output path")
    ap.add_argument(
        "--current_attempt",
        type=int,
        default=1,
        help="Current iteration attempt number (for orchestrator use)",
    )

    # Multi-model support
    ap.add_argument("--claims-model", default=None, help="Model used for claim extraction (for loading claims from model-specific directory)")
    ap.add_argument("--tests-model", default=None, help="Model used for test generation (defaults to --model)")
    ap.add_argument("--use-model-subdirs", action="store_true", help="Use model-specific subdirectories")
    ap.add_argument("--no-model-subdirs", action="store_true", help="Use legacy flat structure (default)")

    return ap.parse_args()


def load_instance(instances_path: Path, instance_id: str) -> Dict[str, Any]:
    """Load instance data from instances.json."""
    data = json.loads(instances_path.read_text())
    record = next((item for item in data if item.get("instance_id") == instance_id), None)
    if not record:
        raise SystemExit(f"Instance {instance_id} not found in {instances_path}")
    return {
        "repo": record["repo"],
        "base_commit": record["base_commit"],
        "patch": record.get("patch"),
        "test_patch": record.get("test_patch"),
        "metadata": {"instance_id": record["instance_id"]},
        "instance_id": record["instance_id"],
    }


def load_claim(
    claims_dir: Path, instance_id: str, claim_id: str
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Load claim data from claims_out directory.

    Supports both flat structure (claims_dir/{instance_id}.json)
    and model-specific structure (claims_dir/{model_slug}/{instance_id}.json)
    """
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


def _reconstruct_plan(plan_dict: Dict[str, Any], context: Any) -> Any:
    """Reconstruct Plan object from serialized dict."""
    from . import planner

    return planner.Plan(
        context=context,
        strategy=plan_dict.get("strategy", ""),
        expected_inputs=plan_dict.get("expected_inputs", ""),
        claim_summary=plan_dict.get("claim_summary", ""),
        grounding_notes=plan_dict.get("grounding_notes", ""),
        issue_context_notes=plan_dict.get("issue_context_notes", ""),
        observables=plan_dict.get("observables", []),
        fixture_notes=plan_dict.get("fixture_notes", []),
        preconditions=plan_dict.get("preconditions", []),
        fallback_strategies=plan_dict.get("fallback_strategies", []),
    )


def run_plan_phase(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Phase 1: Context gathering, planning, test generation.
    Runs outside container in conda env with full dependencies.

    Supports iteration with previous feedback from state file.
    Supports multi-model workflows (extract claims with Model A, generate tests with Model B).
    """
    from claim_test_generation.claim_test_generator import VLLMClient
    from claim_test_generation.generate_claim_tests import _sanitize
    from common.model_paths import MultiModelPaths

    from .context import (
        ClaimContext,
        build_claim_context,
        deserialize_claim_context,
        hash_claim_context,
        serialize_claim_context,
    )
    from .context_builder import enrich_claim_context
    from . import diagnostics, guardrails, planner
    from .pytest_writer import generate_pytest_from_sketch
    from .test_sketcher import generate_test_sketch

    if not args.instance_id:
        raise SystemExit("--instance_id is required for plan phase")

    # Load existing state if it exists (for iterations > 1)
    state = {}
    if args.state_file.exists():
        state = json.loads(args.state_file.read_text())
        print(
            f"Loaded existing state for iteration {state.get('current_attempt', 1)}",
            file=sys.stderr,
        )

    # Extract feedback from previous iteration
    previous_feedback = state.get("previous_feedback")
    previous_diagnosis_dict = state.get("previous_diagnosis")
    previous_diagnosis = None
    if previous_diagnosis_dict:
        previous_diagnosis = diagnostics.Diagnosis(
            label=previous_diagnosis_dict.get("label", ""),
            details=previous_diagnosis_dict.get("details", ""),
        )

    current_attempt = state.get("current_attempt", args.current_attempt)

    # Setup multi-model paths
    use_model_subdirs = args.use_model_subdirs and not args.no_model_subdirs
    if use_model_subdirs:
        claims_model = args.claims_model or args.model
        tests_model = args.tests_model or args.model
        model_paths = MultiModelPaths(
            claims_model=claims_model,
            tests_model=tests_model,
            base_dir=Path.cwd(),
            use_model_subdirs=True
        )
        print(f"Multi-model setup:", file=sys.stderr)
        print(f"  Claims from: {claims_model} -> {model_paths.claims_dir()}", file=sys.stderr)
        print(f"  Tests to: {tests_model} -> {model_paths.tests_root()}", file=sys.stderr)
    else:
        model_paths = None

    # First iteration: build context
    if not state or current_attempt == 1:
        instances_path = Path(args.instances_file).resolve()
        repos_root = Path(args.repos_root).resolve()

        # Determine claims directory
        if model_paths:
            claims_dir = model_paths.claims_dir()
        else:
            claims_dir = Path(args.claims_dir).resolve()

        sample = load_instance(instances_path, args.instance_id)
        claim, issue_context = load_claim(claims_dir, args.instance_id, args.claim_id)

        print(
            f"Building context for {args.instance_id}:{args.claim_id}...",
            file=sys.stderr,
        )
        claim_context = build_claim_context(
            claim=claim,
            sample=sample,
            issue_context=issue_context,
            repos_root=repos_root,
        )
        claim_context = enrich_claim_context(claim_context, repos_root)
        serialized_context = serialize_claim_context(claim_context)
        context_hash = hash_claim_context(serialized_context)

        # Initialize state
        state.update(
            {
                "instance_id": args.instance_id,
                "claim_id": args.claim_id,
                "sample": sample,
                "claim": claim,
                "issue_context": issue_context,
                "context": serialized_context,
                "context_hash": context_hash,
                "attempts": [],
            }
        )
    else:
        # Subsequent iterations: reuse context from state
        sample = state["sample"]
        claim = state["claim"]
        issue_context = state.get("issue_context")
        serialized_context = state["context"]
        context_hash = state["context_hash"]

        # Reconstruct claim_context from serialized form
        claim_context = deserialize_claim_context(serialized_context)

    # Initialize paths and config
    repos_root = Path(args.repos_root).resolve()

    if model_paths:
        tests_root = model_paths.tests_root()
        claim_tests_root = tests_root  # Use same directory for model-specific structure
        # Auto-generate log path if not provided
        if args.log_path:
            log_path = Path(args.log_path).resolve()
        else:
            log_path = model_paths.log_file(args.instance_id, args.claim_id)
    else:
        tests_root = Path(args.tests_root).resolve()
        claim_tests_root = Path(args.claim_tests_root).resolve()
        log_path = Path(args.log_path).resolve() if args.log_path else None

    config_dict = {
        "tests_root": str(tests_root),
        "claim_tests_root": str(claim_tests_root),
        "repos_root": str(repos_root),
        "max_attempts": args.max_attempts,
        "timeout_s": args.timeout_s,
        "log_path": str(log_path) if log_path else None,
    }

    # Add multi-model metadata
    if model_paths:
        config_dict["multi_model"] = model_paths.get_summary()
    else:
        # Store model info even without model subdirs for result tracking
        config_dict["multi_model"] = {
            "tests_model": args.model,
            "claims_model": args.claims_model or args.model,
            "use_model_subdirs": False,
        }

    state.setdefault("config", config_dict)

    # Initialize LLM client
    client = VLLMClient(
        endpoint=args.endpoint,
        model=args.model,
        temperature=0.1,
        max_tokens=4096,
        timeout_s=args.timeout_s,
        api_key=args.api_key,
    )

    # Generate plan (with refinement if we have previous diagnosis)
    print(f"Generating plan (attempt {current_attempt})...", file=sys.stderr)
    if current_attempt == 1:
        static_plan = planner.StaticPlanner(claim_context).build()
        state["static_plan"] = static_plan.to_dict()
    else:
        # Reload static plan from state
        static_plan_dict = state.get("static_plan", {})
        static_plan = _reconstruct_plan(static_plan_dict, claim_context)

    dynamic_planner = planner.DynamicPlanner()
    current_plan = dynamic_planner.refine(static_plan, previous_diagnosis)

    # Check guardrails (pass previous_feedback to allow smart overrides)
    guardrail_result = guardrails.evaluate(current_plan, previous_feedback=previous_feedback)
    if not guardrail_result.ok:
        # Convert guardrail failure into actionable feedback
        from agentic_closed_loop import diagnostics
        diagnosis = diagnostics.classify_guardrail_failure(
            guardrail_result.to_dict(),
            current_plan.to_dict()
        )

        state["attempts"].append(
            {
                "attempt": current_attempt,
                "plan": current_plan.to_dict(),
                "guardrail": guardrail_result.to_dict(),
                "status": "guardrail_failed",
                "failure_classification": diagnosis.to_dict(),
            }
        )

        # Prepare feedback for next iteration
        state["previous_feedback"] = f"{diagnosis.label}: {diagnosis.details}"
        state["previous_diagnosis"] = diagnosis.to_dict()

        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        args.state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))

        print(f"⚠ Guardrail failed: {diagnosis.label}", file=sys.stderr)
        print(f"   Feedback will be provided to next iteration", file=sys.stderr)
        return state

    # Generate test sketch and code
    print("Generating test sketch...", file=sys.stderr)
    guardrail_checks = [check.to_dict() for check in guardrail_result.checks]
    sketch = generate_test_sketch(
        plan=current_plan,
        guardrail_context=guardrail_result.context,
        guardrail_checks=guardrail_checks,
        client=client,
        previous_feedback=previous_feedback,
    )

    print("Generating pytest code...", file=sys.stderr)
    code, checklist_coverage = generate_pytest_from_sketch(
        claim=claim,
        sample=sample,
        plan=current_plan,
        sketch=sketch,
        guardrail_context=guardrail_result.context,
        guardrail_checks=guardrail_checks,
        client=client,
        previous_feedback=previous_feedback,
    )

    # Write test file
    tests_dir = tests_root / (args.instance_id or "unknown_instance")
    tests_dir.mkdir(parents=True, exist_ok=True)
    instance_slug = _sanitize(args.instance_id)
    claim_slug = _sanitize(args.claim_id)
    test_path = tests_dir / f"{instance_slug}__test_claim_{claim_slug}.py"
    test_path.write_text(code, encoding="utf-8")
    test_file_path = str(test_path)

    # Record attempt
    state["attempts"].append(
        {
            "attempt": current_attempt,
            "plan": current_plan.to_dict(),
            "guardrail": guardrail_result.to_dict(),
            "generated_test_path": test_file_path,
            "generated_code": code,
            "test_sketch": sketch.to_dict(),
            "checklist_coverage": checklist_coverage,
            "context_hash": context_hash,
        }
    )

    state["test_file_path"] = test_file_path

    # Save state
    args.state_file.parent.mkdir(parents=True, exist_ok=True)
    args.state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(
        f"Plan phase complete for attempt {current_attempt}. State saved to {args.state_file}",
        file=sys.stderr,
    )

    return state


def run_verify_phase(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Phase 2: Test verification only.
    Runs inside container with minimal dependencies.

    Updates state with diagnosis for next iteration.
    """
    from claim_test_verification import verify_instance

    from . import diagnostics

    if not args.state_file.exists():
        raise SystemExit(f"State file not found: {args.state_file}")

    print(f"Loading state from {args.state_file}...", file=sys.stderr)
    state = json.loads(args.state_file.read_text())

    sample = state["sample"]
    config_dict = state["config"]
    current_attempt = state.get("current_attempt", 1)

    # Run verification
    print(
        f"Verifying {state['instance_id']}:{state['claim_id']} (attempt {current_attempt})...",
        file=sys.stderr,
    )
    result = verify_instance(
        sample=sample,
        claim_tests_root=Path(config_dict["claim_tests_root"]),
        use_container=True,  # Uses instance-specific container
        timeout_s=config_dict["timeout_s"],
        max_claims=1,
    )

    # CRITICAL FIX: Get generated code from last attempt to enable pattern detection
    attempts = state["attempts"]
    generated_code = ""
    if attempts:
        last_attempt = attempts[-1]
        generated_code = last_attempt.get("generated_code", "")

    # Pass generated_code to enable anti-pattern detection
    diagnosis = diagnostics.classify_verification(result, generated_code=generated_code)
    print(f"Diagnosis: {diagnosis.label} - {diagnosis.details}", file=sys.stderr)

    # Update the current attempt with verification results
    if attempts:
        last_attempt = attempts[-1]
        last_attempt["verification_result"] = result
        last_attempt["failure_classification"] = diagnosis.to_dict()
        last_attempt["diagnosis_label"] = diagnosis.label
        last_attempt["diagnosis_details"] = diagnosis.details

    success = diagnosis.label == "success"

    # Save updated state
    args.state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    payload = {
        "instance_id": state["instance_id"],
        "claim_id": state["claim_id"],
        "success": success,
        "diagnosis": diagnosis.to_dict(),
        "attempt": current_attempt,
    }

    print(
        f"Verification complete for attempt {current_attempt}. Results saved to {args.state_file}",
        file=sys.stderr,
    )
    return payload


def main() -> None:
    args = parse_args()

    if args.phase == "plan":
        state = run_plan_phase(args)
        print(json.dumps({"status": "plan_complete", "state_file": str(args.state_file)}, indent=2))

    elif args.phase == "verify":
        payload = run_verify_phase(args)
        print(json.dumps(payload, indent=2))

    elif args.phase == "full":
        # Run both phases (legacy mode for backwards compatibility)
        state = run_plan_phase(args)
        payload = run_verify_phase(args)
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
