from __future__ import annotations

import textwrap
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from claim_test_generation.claim_test_generator import (
    guess_import_from_path,
    pick_primary_grounding_path,
)


@dataclass
class Plan:
    instance_id: str
    claim_id: str
    repo: str
    primary_module: Optional[str]
    target_symbols: List[str]
    strategy: str
    expected_inputs: str
    claim_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def summarize_claim(claim: Dict[str, Any]) -> str:
    pieces = [
        claim.get("claim_text") or "",
        f"GIVEN: {claim.get('given') or ''}",
        f"WHEN: {claim.get('when') or ''}",
        f"THEN: {claim.get('then') or ''}",
    ]
    return " | ".join(part.strip() for part in pieces if part)


def build_strategy(claim: Dict[str, Any], module: Optional[str]) -> str:
    targets = claim.get("target_symbols") or []
    human_targets = ", ".join(targets) if targets else "repository helper"
    if module:
        return (
            f"Import {module} and exercise {human_targets} using parameters implied "
            "by the claim text."
        )
    return (
        "Locate the touched module from the grounding evidence and interact with "
        f"{human_targets} according to the claim."
    )


def collect_expected_inputs(claim: Dict[str, Any]) -> str:
    given = claim.get("given") or ""
    when = claim.get("when") or ""
    then = claim.get("then") or ""
    return textwrap.dedent(
        f"""\
Inputs:
- context: {given.strip() or 'unspecified'}
- action: {when.strip() or 'unspecified'}
- expectation: {then.strip() or 'unspecified'}"""
    )


def create_plan(
    claim: Dict[str, Any],
    *,
    repo: str,
    instance_id: str,
) -> Plan:
    primary_path = pick_primary_grounding_path(claim)
    module = guess_import_from_path(primary_path)
    target_symbols = claim.get("target_symbols") or []
    plan = Plan(
        instance_id=instance_id,
        claim_id=claim.get("claim_id") or "C1",
        repo=repo,
        primary_module=module,
        target_symbols=target_symbols,
        strategy=build_strategy(claim, module),
        expected_inputs=collect_expected_inputs(claim),
        claim_summary=summarize_claim(claim),
    )
    return plan


def plan_to_messages(
    plan: Plan,
    guardrail_context: Optional[Dict[str, Any]] = None,
    previous_feedback: Optional[str] = None,
) -> List[Dict[str, str]]:
    lines = [
        f"Plan for {plan.instance_id}:{plan.claim_id}",
        f"Repository: {plan.repo}",
        f"Target module: {plan.primary_module or 'unknown'}",
        f"Target symbols: {', '.join(plan.target_symbols) or 'unspecified'}",
        f"Strategy: {plan.strategy}",
        plan.expected_inputs,
        f"Claim summary: {plan.claim_summary}",
    ]
    if guardrail_context:
        lines.append(f"Guardrail context: {guardrail_context}")
    if previous_feedback:
        lines.append(f"Previous failure diagnosis: {previous_feedback}")
    user_prompt = "\n".join(lines)
    return [{"role": "user", "content": user_prompt}]
