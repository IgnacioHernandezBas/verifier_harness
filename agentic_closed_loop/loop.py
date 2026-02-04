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


@dataclass
class LoopConfig:
    tests_root: Path
    claim_tests_root: Path
    max_attempts: int = 3
    timeout_s: int = 300
    log_path: Optional[Path] = None


CHECKLIST_PROMPT = (
    "Before writing the pytest, emit a three-line checklist as Python comments "
    "exactly in this format:\n"
    "# Chosen strategy: <CLI | unit | hybrid>\n"
    "# Key observable(s) asserted: <observable details>\n"
    "# Inputs/fixtures used: <inputs or fixtures>\n"
    "Immediately after the checklist, output the pytest code."
)


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
        self.issue_context = issue_context
        self.instance_id = sample.get("metadata", {}).get("instance_id") or sample.get(
            "instance_id"
        )
        self.claim_id = claim.get("claim_id") or "C1"
        self.logs: List[Dict[str, Any]] = []

    def _tests_dir(self) -> Path:
        return self.config.tests_root / (self.instance_id or "unknown_instance")

    def _write_test(self, code: str) -> Path:
        self._tests_dir().mkdir(parents=True, exist_ok=True)
        instance_slug = _sanitize(self.instance_id)
        claim_slug = _sanitize(self.claim_id)
        path = self._tests_dir() / f"{instance_slug}__test_claim_{claim_slug}.py"
        path.write_text(code, encoding="utf-8")
        return path

    def run(self) -> Dict[str, Any]:
        previous_feedback: Optional[str] = None
        success = False
        failure_reason: Optional[str] = None

        for attempt in range(1, self.config.max_attempts + 1):
            current_plan = planner.create_plan(
                self.claim,
                repo=self.sample.get("repo", "unknown_repo"),
                instance_id=self.instance_id,
            )
            guardrail_result = guardrails.evaluate(current_plan)

            if not guardrail_result.ok:
                failure_reason = guardrail_result.reason or "guardrail_failed"
                self.logs.append(
                    {
                        "attempt": attempt,
                        "plan": current_plan.to_dict(),
                        "guardrail": guardrail_result.to_dict(),
                        "status": "guardrail_failed",
                        "failure_classification": failure_reason,
                    }
                )
                break

            prompt_messages = planner.plan_to_messages(
                current_plan,
                guardrail_context=guardrail_result.context,
                previous_feedback=previous_feedback,
            )
            context_pack = _build_issue_context_message(self.claim, self.issue_context)
            if context_pack:
                prompt_messages.append({"role": "user", "content": context_pack})
            prompt_messages.append({"role": "user", "content": CHECKLIST_PROMPT})
            code = generate_pytest_for_claim(
                self.claim,
                repo=self.sample.get("repo", "unknown_repo"),
                instance_id=self.instance_id or "unknown_instance",
                client=self.client,
                extra_messages=prompt_messages,
            )
            test_path = self._write_test(code)

            result = verify_instance(
                sample=self.sample,
                claim_tests_root=self.config.claim_tests_root,
                use_container=True,
                timeout_s=self.config.timeout_s,
                max_claims=1,
            )
            diagnosis = diagnostics.classify_verification(result)
            attempt_log = {
                "attempt": attempt,
                "plan": current_plan.to_dict(),
                "guardrail": guardrail_result.to_dict(),
                "generated_test_path": str(test_path),
                "generated_code": code,
                "verification_result": result,
                "failure_classification": diagnosis.to_dict(),
            }
            self.logs.append(attempt_log)

            if diagnosis.label == "success":
                success = True
                break

            previous_feedback = f"{diagnosis.label}: {diagnosis.details}"
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
        if self.config.log_path:
            self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.config.log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload


def _build_issue_context_message(
    claim: Dict[str, Any], issue_context: Optional[Dict[str, Any]]
) -> Optional[str]:
    if not issue_context:
        return None

    refs = claim.get("issue_context_refs") or {}

    sections: List[str] = []
    mapping = (
        ("cli_command_ids", "cli_commands", "CLI commands", "command"),
        ("expected_output_block_ids", "expected_output_blocks", "Expected output", "content"),
        ("code_block_ids", "code_blocks", "Repro/code snippet", "content"),
        ("traceback_ids", "tracebacks", "Traceback", "content"),
    )

    for ref_key, ctx_key, label, value_key in mapping:
        ids = refs.get(ref_key) or []
        if not ids:
            continue
        entries = issue_context.get(ctx_key) or []
        selected = []
        for idx in ids:
            if not isinstance(idx, int):
                continue
            if idx < 0 or idx >= len(entries):
                continue
            entry = entries[idx]
            value = entry.get(value_key)
            if not value:
                continue
            selected.append(value)
        if not selected:
            continue
        section_lines = [f"- {label}:"]
        for text in selected:
            section_lines.append(f"  - {_indent_multiline(text)}")
        sections.append("\n".join(section_lines))

    if not sections:
        return None

    header = "Additional issue grounding (verbatim):"
    footer = "Use this grounding to design the pytest. Prefer reproducing the observable behavior."
    return "\n".join([header, *sections, footer])


def _indent_multiline(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n")
    lines = normalized.split("\n")
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    indented = "\n    ".join(lines)
    return indented
