#!/usr/bin/env python3
"""
Orchestrator for iterative hybrid agentic loop.

Manages the feedback loop between planning (host) and verification (container) phases.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class LoopOrchestrator:
    """
    Manages iterative execution of plan → verify → feedback loop.
    """

    def __init__(
        self,
        *,
        state_file: Path,
        instance_id: str,
        claim_id: str,
        max_attempts: int,
        singularity_image: Optional[Path],
        conda_env: str,
        common_args: list[str],
        auto_detect_container: bool = True,
    ):
        self.state_file = state_file
        self.instance_id = instance_id
        self.claim_id = claim_id
        self.max_attempts = max_attempts
        self.conda_env = conda_env
        self.common_args = common_args

        # Resolve container: prefer instance-specific, fall back to provided/generic
        if auto_detect_container:
            print(f"Resolving instance-specific container for {instance_id}...", file=sys.stderr)
            resolved_container = self._resolve_instance_container(instance_id)
            if resolved_container:
                self.singularity_image = resolved_container
                print(f"Using instance-specific container: {resolved_container}", file=sys.stderr)
            else:
                print(f"Warning: Could not resolve instance-specific container, falling back to provided/generic", file=sys.stderr)
                self.singularity_image = singularity_image
                if singularity_image:
                    print(f"Using fallback container: {singularity_image}", file=sys.stderr)
        else:
            self.singularity_image = singularity_image
            if singularity_image:
                print(f"Using provided container: {singularity_image}", file=sys.stderr)

    def _resolve_instance_container(self, instance_id: str) -> Optional[Path]:
        """
        Resolve instance-specific Singularity container.
        Returns None if container cannot be built/found.
        """
        try:
            from claim_test_verification.claim_test_verifier import _build_or_get_container

            container_path = _build_or_get_container(instance_id)
            return container_path
        except Exception as e:
            print(f"Error resolving container: {e}", file=sys.stderr)
            return None

    def run(self) -> Dict[str, Any]:
        """
        Execute the iterative feedback loop.

        Returns:
            Final payload with results
        """
        # Initialize state if needed
        if not self.state_file.exists():
            self._initialize_state()

        for attempt in range(1, self.max_attempts + 1):
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"ITERATION {attempt}/{self.max_attempts}", file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)

            # Load current state
            state = self._load_state()
            state["current_attempt"] = attempt
            self._save_state(state)

            # PHASE 1: Planning (host environment)
            print(f"→ Running PLAN phase (attempt {attempt})...", file=sys.stderr)
            plan_success = self._run_plan_phase(attempt)
            if not plan_success:
                return self._handle_plan_failure()

            # Check for guardrail failure - but don't exit immediately, check if stuck first
            state = self._load_state()
            if self._check_guardrail_failure(state):
                # Check if we should exit due to repeated failures
                exit_decision = self._should_exit(state, attempt)
                if exit_decision["should_exit"]:
                    print(f"\n✗ Exiting: {exit_decision['reason']}", file=sys.stderr)
                    return self._finalize_results(state, exit_decision)

                # Guardrail failed but we should continue - prepare feedback and skip verification
                print(f"⚠ Guardrail failed (attempt {attempt}), preparing feedback for next iteration...", file=sys.stderr)
                self._prepare_next_iteration(state)
                continue  # Skip verification phase, go to next iteration

            # PHASE 2: Verification (container)
            print(f"→ Running VERIFY phase (attempt {attempt})...", file=sys.stderr)
            verify_success = self._run_verify_phase()
            if not verify_success:
                return self._handle_verify_failure()

            # PHASE 3: Check exit conditions
            state = self._load_state()
            exit_decision = self._should_exit(state, attempt)

            if exit_decision["should_exit"]:
                print(f"\n✓ Exiting: {exit_decision['reason']}", file=sys.stderr)
                return self._finalize_results(state, exit_decision)

            # PHASE 4: Prepare feedback for next iteration
            print(f"→ Preparing feedback for next iteration...", file=sys.stderr)
            self._prepare_next_iteration(state)

        # Max attempts reached
        print(
            f"\n⚠ Maximum attempts ({self.max_attempts}) reached", file=sys.stderr
        )
        state = self._load_state()
        return self._finalize_results(
            state, {"reason": "max_attempts_reached", "should_exit": True}
        )

    def _run_plan_phase(self, attempt: int) -> bool:
        """Execute planning phase via subprocess."""
        cmd = [
            "conda",
            "run",
            "-n",
            self.conda_env,
            "python",
            "-m",
            "agentic_closed_loop.run_agentic_loop_hybrid",
            "--phase",
            "plan",
            "--current_attempt",
            str(attempt),
            *self.common_args,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"ERROR: Plan phase failed:\n{result.stderr}", file=sys.stderr)
            return False

        if result.stdout:
            print(result.stdout, file=sys.stderr)
        return True

    def _run_verify_phase(self) -> bool:
        """Execute verification phase on host (not in container).

        Note: verify_instance will handle container execution internally.
        """
        # Always run verify phase on host with conda environment
        # It will manage containers internally via verify_instance
        cmd = [
            "conda",
            "run",
            "-n",
            self.conda_env,
            "python",
            "-m",
            "agentic_closed_loop.run_agentic_loop_hybrid",
            "--phase",
            "verify",
            "--state_file",
            str(self.state_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"ERROR: Verify phase failed:\n{result.stderr}", file=sys.stderr)
            return False

        if result.stdout:
            print(result.stdout, file=sys.stderr)
        return True

    def _check_guardrail_failure(self, state: Dict[str, Any]) -> bool:
        """Check if the last attempt had a guardrail failure."""
        attempts = state.get("attempts", [])
        if not attempts:
            return False

        last_attempt = attempts[-1]
        status = last_attempt.get("status")
        if status == "guardrail_failed":
            return True

        guardrail = last_attempt.get("guardrail", {})
        return not guardrail.get("ok", True)

    def _should_exit(self, state: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        """
        Determine if loop should exit based on current state.

        Returns:
            {"should_exit": bool, "reason": str}
        """
        attempts = state.get("attempts", [])
        if not attempts:
            return {"should_exit": False, "reason": ""}

        last_attempt = attempts[-1]
        diagnosis = last_attempt.get("failure_classification", {})
        label = diagnosis.get("label", "")

        # Exit condition 1: Success
        if label == "success":
            return {"should_exit": True, "reason": "success"}

        # Exit condition 2: Non-discriminative (can't improve)
        if label == "non_discriminative":
            return {
                "should_exit": True,
                "reason": "non_discriminative - test passes in both bug and gold",
            }

        # Exit condition 3: Repeated identical errors (stuck in loop)
        if attempt >= 3 and len(attempts) >= 3:
            # Check if last 3 attempts have identical error labels
            recent_labels = [
                att.get("failure_classification", {}).get("label", "")
                for att in attempts[-3:]
            ]
            if len(set(recent_labels)) == 1 and recent_labels[0]:
                # Same error 3 times in a row - check if it's a type we should exit on
                error_label = recent_labels[0]
                # CRITICAL FIX: Exit on repeated failures that indicate the LLM is not learning
                # Added "internal_import_error" and other stuck patterns
                if error_label in [
                    "signature_mismatch", "import_error", "fixture_missing",
                    "signature_check", "import_check_failed", "probe_check_failed",
                    "internal_import_error",  # FIX: Was missing, caused UNRESOLVED instances to waste attempts
                    "mocking_error",  # Also exit on repeated mocking issues
                    "environment_error"  # Environment issues won't be fixed by retrying
                ] or error_label.startswith("stuck_in_guardrail_loop_"):
                    return {
                        "should_exit": True,
                        "reason": f"stuck_in_loop - same '{error_label}' error 3 times, LLM not learning from feedback",
                    }

        # Exit condition 4: Specific guardrail loop detection (from loop.py)
        if last_attempt.get("status") == "guardrail_failed":
            failure_classification = last_attempt.get("failure_classification", {})
            if isinstance(failure_classification, dict):
                label = failure_classification.get("label", "")
            else:
                label = str(failure_classification)

            if label.startswith("stuck_in_guardrail_loop_"):
                return {
                    "should_exit": True,
                    "reason": label,
                }

        # Continue iterating
        return {"should_exit": False, "reason": ""}

    def _prepare_next_iteration(self, state: Dict[str, Any]) -> None:
        """
        Extract diagnosis from last attempt and prepare feedback for next iteration.
        Handles both verification failures and guardrail failures.
        """
        attempts = state.get("attempts", [])
        if not attempts:
            return

        last_attempt = attempts[-1]
        diagnosis_dict = last_attempt.get("failure_classification", {})

        if diagnosis_dict:
            # Handle both dict and string failure classifications
            if isinstance(diagnosis_dict, dict):
                label = diagnosis_dict.get("label", "")
                details = diagnosis_dict.get("details", "")
            else:
                # Legacy string format
                label = str(diagnosis_dict)
                details = ""

            # Format feedback string (matches loop.py:174)
            if details:
                state["previous_feedback"] = f"{label}: {details}"
            else:
                state["previous_feedback"] = label

            state["previous_diagnosis"] = diagnosis_dict
            state["should_continue"] = True

        self._save_state(state)

        # Show feedback preview
        feedback_preview = state.get('previous_feedback', 'None')
        if len(feedback_preview) > 200:
            feedback_preview = feedback_preview[:200] + "..."
        print(
            f"   Feedback: {feedback_preview}", file=sys.stderr
        )

    def _load_state(self) -> Dict[str, Any]:
        """Load state from JSON file."""
        return json.loads(self.state_file.read_text())

    def _save_state(self, state: Dict[str, Any]) -> None:
        """Save state to JSON file."""
        self.state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    def _initialize_state(self) -> None:
        """Create initial empty state."""
        initial_state = {
            "instance_id": self.instance_id,
            "claim_id": self.claim_id,
            "current_attempt": 0,
            "max_attempts": self.max_attempts,
            "should_continue": True,
            "previous_feedback": None,
            "previous_diagnosis": None,
            "attempts": [],
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._save_state(initial_state)

    def _finalize_results(
        self, state: Dict[str, Any], exit_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Finalize results and update state.
        """
        attempts = state.get("attempts", [])
        success = exit_decision.get("reason") == "success"

        payload = {
            "instance_id": state.get("instance_id"),
            "claim_id": state.get("claim_id"),
            "success": success,
            "attempts": attempts,
            "failure_reason": None if success else exit_decision.get("reason"),
            "total_attempts": len(attempts),
        }

        state["verification_complete"] = True
        state["final_payload"] = payload
        state["exit_reason"] = exit_decision.get("reason")
        state["should_continue"] = False
        self._save_state(state)

        # Generate result summary
        self._generate_result_summary(state)

        return payload

    def _generate_result_summary(self, state: Dict[str, Any]) -> None:
        """Generate human-readable result summary."""
        try:
            from .result_summarizer import create_result_summary
            import os

            # Extract model info from common_args or state
            tests_model = None
            claims_model = None

            for i, arg in enumerate(self.common_args):
                if arg == "--model" and i + 1 < len(self.common_args):
                    tests_model = self.common_args[i + 1]
                elif arg == "--claims-model" and i + 1 < len(self.common_args):
                    claims_model = self.common_args[i + 1]

            # Fallback to config if available
            if not tests_model:
                config = state.get("config", {})
                multi_model = config.get("multi_model", {})
                tests_model = multi_model.get("tests_model", "unknown")
                claims_model = multi_model.get("claims_model", tests_model)

            slurm_job_id = os.getenv("SLURM_JOB_ID")

            create_result_summary(
                state_file=self.state_file,
                tests_model=tests_model or "unknown",
                claims_model=claims_model,
                slurm_job_id=slurm_job_id,
            )
        except Exception as e:
            print(f"Warning: Failed to generate result summary: {e}", file=sys.stderr)

    def _handle_plan_failure(self) -> Dict[str, Any]:
        """Handle planning phase failure."""
        return {
            "instance_id": self.instance_id,
            "claim_id": self.claim_id,
            "success": False,
            "failure_reason": "plan_phase_error",
            "attempts": [],
        }

    def _handle_verify_failure(self) -> Dict[str, Any]:
        """Handle verification phase failure."""
        state = self._load_state()
        return {
            "instance_id": self.instance_id,
            "claim_id": self.claim_id,
            "success": False,
            "failure_reason": "verify_phase_error",
            "attempts": state.get("attempts", []),
        }


def main():
    """CLI entry point for orchestrator."""
    parser = argparse.ArgumentParser(
        description="Orchestrate iterative hybrid agentic loop"
    )
    parser.add_argument("--state_file", type=Path, required=True)
    parser.add_argument("--instance_id", required=True)
    parser.add_argument("--claim_id", default="C1")
    parser.add_argument("--max_attempts", type=int, default=3)
    parser.add_argument("--singularity_image", type=Path, default=None)
    parser.add_argument(
        "--auto_detect_container",
        action="store_true",
        default=True,
        help="Auto-detect instance-specific container (default: True)",
    )
    parser.add_argument(
        "--no_auto_detect_container",
        dest="auto_detect_container",
        action="store_false",
        help="Disable auto-detection, use provided --singularity_image",
    )
    parser.add_argument("--conda_env", default="verifier_llm")

    # Accept remaining args to pass to hybrid script
    parser.add_argument("--claims_dir", default="claim_extraction/claims_out")
    parser.add_argument("--instances_file", default="claim_extraction/instances.json")
    parser.add_argument("--tests_root", default="claim_test_generation/tests_out")
    parser.add_argument(
        "--claim_tests_root", default="claim_test_generation/tests_out"
    )
    parser.add_argument("--repos_root", default="repos_temp_demo")
    parser.add_argument("--timeout_s", type=int, default=300)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api_key", default=None)
    parser.add_argument("--log_path", default=None)

    # Multi-model support
    parser.add_argument("--claims-model", dest="claims_model", default=None, help="Model used for claim extraction")
    parser.add_argument("--tests-model", dest="tests_model", default=None, help="Model used for test generation")
    parser.add_argument("--use-model-subdirs", dest="use_model_subdirs", action="store_true", help="Use model-specific subdirectories")

    args = parser.parse_args()

    # Build common args for hybrid script
    common_args = [
        "--state_file",
        str(args.state_file),
        "--instance_id",
        args.instance_id,
        "--claim_id",
        args.claim_id,
        "--max_attempts",
        str(args.max_attempts),
        "--claims_dir",
        args.claims_dir,
        "--instances_file",
        args.instances_file,
        "--tests_root",
        args.tests_root,
        "--claim_tests_root",
        args.claim_tests_root,
        "--repos_root",
        args.repos_root,
        "--endpoint",
        args.endpoint,
        "--model",
        args.model,
        "--timeout_s",
        str(args.timeout_s),
    ]
    if args.api_key:
        common_args.extend(["--api_key", args.api_key])
    if args.log_path:
        common_args.extend(["--log_path", args.log_path])

    # Add multi-model support args
    if args.claims_model:
        common_args.extend(["--claims-model", args.claims_model])
    if args.tests_model:
        common_args.extend(["--tests-model", args.tests_model])
    if args.use_model_subdirs:
        common_args.append("--use-model-subdirs")

    orchestrator = LoopOrchestrator(
        state_file=args.state_file,
        instance_id=args.instance_id,
        claim_id=args.claim_id,
        max_attempts=args.max_attempts,
        singularity_image=args.singularity_image,
        conda_env=args.conda_env,
        common_args=common_args,
        auto_detect_container=args.auto_detect_container,
    )

    payload = orchestrator.run()
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
