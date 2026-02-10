from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from claim_test_generation.claim_test_generator import VLLMClient

from .planner import Plan, plan_to_messages


SKETCH_SYSTEM_PROMPT = (
    "You are an expert Python test planner. Produce precise pytest plans before any code is written. "
    "Respond ONLY with valid JSON matching the provided schema."
)

SKETCH_SCHEMA_DESCRIPTION = """
Return JSON with these keys:
- "strategy": short string describing overall approach.
- "assertions": array of observable checks to perform (strings).
- "fixtures": array of STANDARD pytest fixtures to use (tmp_path, monkeypatch, capsys ONLY - NO repo-specific fixtures).
- "data_setup": array describing concrete inputs / data arrangement (strings).
- "edge_cases": array with optional negative/edge case ideas (strings).
- "checklist": array of 3 concise sentences (<=80 chars) summarizing what the eventual pytest MUST show.
"""


@dataclass
class TestSketch:
    strategy: str
    assertions: List[str]
    fixtures: List[str]
    data_setup: List[str]
    edge_cases: List[str]
    checklist: List[str]
    raw: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_prompt_block(self) -> str:
        payload = {
            "strategy": self.strategy,
            "assertions": self.assertions,
            "fixtures": self.fixtures,
            "data_setup": self.data_setup,
            "edge_cases": self.edge_cases,
            "checklist": self.checklist,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_test_sketch(
    *,
    plan: Plan,
    guardrail_context: Dict[str, Any],
    guardrail_checks: List[Dict[str, Any]],
    client: VLLMClient,
    previous_feedback: Optional[str],
) -> TestSketch:
    plan_messages = plan_to_messages(plan, guardrail_context, previous_feedback)
    plan_block = "\n\n".join(message["content"] for message in plan_messages)
    guardrail_block = json.dumps(
        {"context": guardrail_context, "checks": guardrail_checks},
        ensure_ascii=False,
        indent=2,
    )
    instructions = (
        f"{SKETCH_SCHEMA_DESCRIPTION}\n"
        "Use the plan and guardrail context below to craft the JSON:\n"
        f"{plan_block}\n\nGuardrail diagnostics:\n{guardrail_block}\n"
        f"Previous failure feedback: {previous_feedback or 'None'}\n"
        "Do not write pytest code yet."
    )
    messages = [
        {"role": "system", "content": SKETCH_SYSTEM_PROMPT},
        {"role": "user", "content": instructions},
    ]
    raw = client.chat(messages)
    parsed = _safe_parse_json(raw)
    if parsed is None:
        parsed = _fallback_payload(plan)
    return TestSketch(
        strategy=_ensure_str(parsed.get("strategy")),
        assertions=_ensure_str_list(parsed.get("assertions")),
        fixtures=_ensure_str_list(parsed.get("fixtures")),
        data_setup=_ensure_str_list(parsed.get("data_setup")),
        edge_cases=_ensure_str_list(parsed.get("edge_cases")),
        checklist=_ensure_checklist(parsed.get("checklist")),
        raw=raw,
    )


def _safe_parse_json(raw: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(raw)
    except Exception:
        # Try to locate JSON substring.
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start : end + 1]
            try:
                return json.loads(snippet)
            except Exception:
                return None
        return None


def _fallback_payload(plan: Plan) -> Dict[str, Any]:
    return {
        "strategy": plan.strategy,
        "assertions": plan.observables[:3],
        "fixtures": plan.fixture_notes[:3],
        "data_setup": [plan.expected_inputs],
        "edge_cases": [],
        "checklist": [
            "Document chosen strategy in comments.",
            "Assert observable(s) quoted in plan.",
            "Explain fixtures or inputs used.",
        ],
    }


def _ensure_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ensure_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    results: List[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                results.append(cleaned)
    return results


def _ensure_checklist(value: Any) -> List[str]:
    items = _ensure_str_list(value)
    if not items:
        return [
            "Checklist: describe strategy comment.",
            "Checklist: assert observable outcome.",
            "Checklist: specify fixtures/data used.",
        ]
    return items[:5]
