from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from claim_test_generation.claim_test_generator import (
    VLLMClient,
    generate_pytest_for_claim,
)
from claim_test_generation.generate_claim_tests import _sanitize
from claim_test_verification import verify_instance

from . import diagnostics, guardrails, planner
from .context import (
    ClaimContext,
    build_claim_context,
    hash_claim_context,
    serialize_claim_context,
)
from .context_builder import enrich_claim_context
from .pytest_writer import generate_pytest_from_sketch
from .test_sketcher import TestSketch, generate_test_sketch


@dataclass
class LoopConfig:
    tests_root: Path
    claim_tests_root: Path
    repos_root: Optional[Path] = None
    max_attempts: int = 3
    timeout_s: int = 300
    log_path: Optional[Path] = None


class AgenticClosedLoop:
    def __init__(
        self,
        *,
        sample: Dict[str, Any],
        claim: Dict[str, Any],
        client: VLLMClient,
        config: LoopConfig,
        issue_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.sample = sample
        self.claim = claim
        self.client = client
        self.config = config
        self.instance_id = sample.get("metadata", {}).get("instance_id") or sample.get(
            "instance_id"
        )
        self.claim_id = claim.get("claim_id") or "C1"
        self.logs: List[Dict[str, Any]] = []
        self.claim_context: ClaimContext = build_claim_context(
            claim=claim,
            sample=sample,
            issue_context=issue_context,
            repos_root=config.repos_root,
        )
        self.claim_context = enrich_claim_context(self.claim_context, config.repos_root)
        self._serialized_context = serialize_claim_context(self.claim_context)
        self._context_hash = hash_claim_context(self._serialized_context)
        self._static_plan = planner.StaticPlanner(self.claim_context).build()
        self._dynamic_planner = planner.DynamicPlanner()

    def _tests_dir(self) -> Path:
        return self.config.tests_root / (self.instance_id or "unknown_instance")

    def _write_test(self, code: str) -> Path:
        self._tests_dir().mkdir(parents=True, exist_ok=True)
        instance_slug = _sanitize(self.instance_id)
        claim_slug = _sanitize(self.claim_id)
        path = self._tests_dir() / f"{instance_slug}__test_claim_{claim_slug}.py"
        path.write_text(code, encoding="utf-8")
        return path

    def _reset_log_file(self) -> None:
        if not self.config.log_path:
            return
        self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.log_path.write_text("", encoding="utf-8")

    def _append_log_event(self, event: Dict[str, Any]) -> None:
        if not self.config.log_path:
            return
        line = json.dumps(event, ensure_ascii=False)
        with self.config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def run(self) -> Dict[str, Any]:
        self._reset_log_file()
        self._append_log_event(
            {
                "event": "claim_context",
                "context_hash": self._context_hash,
                "context": self._serialized_context,
            }
        )
        previous_feedback: Optional[str] = None
        previous_diagnosis: Optional[diagnostics.Diagnosis] = None
        previous_code: Optional[str] = None
        previous_patterns: Optional[List[Dict[str, Any]]] = None
        success = False
        failure_reason: Optional[str] = None

        for attempt in range(1, self.config.max_attempts + 1):
            current_plan = self._dynamic_planner.refine(self._static_plan, previous_diagnosis)
            guardrail_result = guardrails.evaluate(current_plan, previous_feedback=previous_feedback)

            if not guardrail_result.ok:
                # Convert guardrail failure into actionable feedback
                diagnosis = diagnostics.classify_guardrail_failure(
                    guardrail_result.to_dict(),
                    current_plan.to_dict()
                )
                failure_reason = diagnosis.label

                attempt_log = {
                    "attempt": attempt,
                    "plan": current_plan.to_dict(),
                    "guardrail": guardrail_result.to_dict(),
                    "status": "guardrail_failed",
                    "failure_classification": diagnosis.to_dict(),
                    "context_hash": self._context_hash,
                }
                self.logs.append(attempt_log)
                self._append_log_event({"event": "attempt", **attempt_log})

                # Set feedback for next iteration
                previous_feedback = f"{diagnosis.label}: {diagnosis.details}"
                previous_diagnosis = diagnosis

                # Check if stuck in same guardrail failure (prevents infinite loops)
                if attempt >= 3:
                    recent_attempts = self.logs[-3:]
                    recent_guardrail_failures = [
                        log.get("failure_classification", {}).get("label", "")
                        for log in recent_attempts
                        if log.get("status") == "guardrail_failed"
                    ]
                    if len(recent_guardrail_failures) == 3 and len(set(recent_guardrail_failures)) == 1:
                        # Same guardrail failure 3 times in a row - exit
                        failure_reason = f"stuck_in_guardrail_loop_{diagnosis.label}"
                        break

                # Continue to next iteration with feedback
                continue

            guardrail_checks = [check.to_dict() for check in guardrail_result.checks]
            sketch = generate_test_sketch(
                plan=current_plan,
                guardrail_context=guardrail_result.context,
                guardrail_checks=guardrail_checks,
                client=self.client,
                previous_feedback=previous_feedback,
            )
            code, checklist_coverage = generate_pytest_from_sketch(
                claim=self.claim,
                sample=self.sample,
                plan=current_plan,
                sketch=sketch,
                guardrail_context=guardrail_result.context,
                guardrail_checks=guardrail_checks,
                client=self.client,
                previous_feedback=previous_feedback,
                previous_code=previous_code,
                previous_patterns=previous_patterns,
            )
            test_path = self._write_test(code)

            result = verify_instance(
                sample=self.sample,
                claim_tests_root=self.config.claim_tests_root,
                use_container=True,
                timeout_s=self.config.timeout_s,
                max_claims=1,
            )
            diagnosis = diagnostics.classify_verification(result, generated_code=code)
            attempt_log = {
                "attempt": attempt,
                "plan": current_plan.to_dict(),
                "guardrail": guardrail_result.to_dict(),
                "generated_test_path": str(test_path),
                "generated_code": code,
                "test_sketch": sketch.to_dict(),
                "checklist_coverage": checklist_coverage,
                "verification_result": result,
                "failure_classification": diagnosis.to_dict(),
                "context_hash": self._context_hash,
            }
            self.logs.append(attempt_log)
            self._append_log_event({"event": "attempt", **attempt_log})

            if diagnosis.label == "success":
                success = True
                break

            previous_feedback = f"{diagnosis.label}: {diagnosis.details}"
            previous_diagnosis = diagnosis
            previous_code = code
            previous_patterns = diagnosis.patterns
            failure_reason = diagnosis.label

            if diagnosis.label == "non_discriminative":
                break

        payload = {
            "instance_id": self.instance_id,
            "claim_id": self.claim_id,
            "success": success,
            "attempts": self.logs,
            "failure_reason": None if success else failure_reason,
        }
        self._append_log_event(
            {
                "event": "summary",
                "context_hash": self._context_hash,
                "payload": payload,
            }
        )
        return payload




    def _reset_log_file(self) -> None:
        if not self.config.log_path:
            return
        self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.log_path.write_text("", encoding="utf-8")

    def _append_log_event(self, event: Dict[str, Any]) -> None:
        if not self.config.log_path:
            return
        line = json.dumps(event, ensure_ascii=False)
        with self.config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
