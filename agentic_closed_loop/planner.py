from __future__ import annotations

import textwrap
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .context import (
    ClaimContext,
    FixtureInfo,
    GroundingEvidence,
    IssueContext,
)
from .diagnostics import Diagnosis


@dataclass
class Plan:
    context: ClaimContext
    strategy: str
    expected_inputs: str
    claim_summary: str
    grounding_notes: str
    issue_context_notes: str
    observables: List[str]
    fixture_notes: List[str]
    preconditions: List[str]
    fallback_strategies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def instance_id(self) -> str:
        return self.context.instance_id

    @property
    def claim_id(self) -> str:
        return self.context.claim_id

    @property
    def repo(self) -> str:
        return self.context.repo

    @property
    def primary_module(self) -> Optional[str]:
        return self.context.primary_module

    @property
    def target_symbols(self) -> List[str]:
        return list(self.context.target_symbols)


def summarize_claim(context: ClaimContext) -> str:
    pieces = [
        context.claim_text,
        f"GIVEN: {context.given}",
        f"WHEN: {context.when}",
        f"THEN: {context.then}",
    ]
    return " | ".join(part.strip() for part in pieces if part)


def build_strategy(context: ClaimContext) -> str:
    module = context.primary_module
    targets = context.target_symbols
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


def collect_expected_inputs(context: ClaimContext) -> str:
    return textwrap.dedent(
        f"""\
Inputs:
- context: {context.given or 'unspecified'}
- action: {context.when or 'unspecified'}
- expectation: {context.then or 'unspecified'}"""
    )


def _shorten(text: str, width: int = 160) -> str:
    clean = " ".join(text.split())
    if len(clean) <= width:
        return clean
    return f"{clean[: width - 1]}…"


def _summarize_grounding(evidence: List[GroundingEvidence]) -> str:
    if not evidence:
        return ""
    lines = ["Grounding evidence:"]
    for item in evidence[:3]:
        parts = []
        if item.symbol:
            parts.append(item.symbol)
        if item.path:
            parts.append(f"path={item.path}")
        if item.snippet:
            parts.append(f"snippet={_shorten(item.snippet)}")
        if item.source_excerpt:
            parts.append(f"excerpt={_shorten(item.source_excerpt)}")
        lines.append(f"- {' | '.join(parts)}")
    if len(evidence) > 3:
        lines.append(f"- (+{len(evidence) - 3} more references)")
    return "\n".join(lines)


def _summarize_issue_context(issue: IssueContext) -> str:
    segments: List[str] = []

    def append(label: str, values: List[str], limit: int = 2) -> None:
        if not values:
            return
        for value in values[:limit]:
            segments.append(f"- {label}: {_shorten(value)}")
        if len(values) > limit:
            segments.append(f"- {label}: (+{len(values) - limit} more)")

    append("CLI", issue.cli_commands)
    append("Code", issue.code_blocks)
    append("Expected output", issue.expected_outputs)
    append("Traceback", issue.tracebacks)

    if not segments:
        return ""
    return "Issue context:\n" + "\n".join(segments)


def _collect_observables(context: ClaimContext) -> List[str]:
    observables: List[str] = []
    if context.then:
        observables.append(f"Assertion target: {context.then}")
    for snippet in context.issue_context.expected_outputs[:3]:
        observables.append(f"Expected output sample: {_shorten(snippet)}")
    for block in context.issue_context.code_blocks[:2]:
        observables.append(f"Code reference: {_shorten(block)}")
    return observables


def _collect_fixture_notes(fixtures: List[FixtureInfo]) -> List[str]:
    notes: List[str] = []
    for info in fixtures[:6]:
        parts = [info.name]
        if info.scope:
            parts.append(f"scope={info.scope}")
        if info.params:
            parts.append(f"params={','.join(info.params[:3])}")
        if info.path:
            parts.append(f"path={info.path}")
        notes.append(" | ".join(parts))
    return notes


def _collect_preconditions(context: ClaimContext) -> List[str]:
    preconditions: List[str] = []
    if not context.primary_file_exists:
        preconditions.append("Primary file missing in repo checkout.")
    else:
        preconditions.append("Primary file located in repo.")
    if context.commit_diff.base_commit:
        preconditions.append(f"Base commit: {context.commit_diff.base_commit}")
    if context.signatures:
        for sig in context.signatures[:3]:
            if sig.signature:
                preconditions.append(f"Signature {sig.signature}")
    return preconditions


def _collect_fallbacks(context: ClaimContext) -> List[str]:
    fallbacks: List[str] = []
    if context.touched_paths:
        fallbacks.append(f"Inspect touched paths: {', '.join(context.touched_paths[:3])}")
    if context.symbol_snippets:
        fallbacks.append("Use gathered symbol snippets to confirm behavior.")
    fallbacks.append("Create all necessary objects directly in the test function (no repo fixtures).")
    return fallbacks


class StaticPlanner:
    def __init__(self, context: ClaimContext) -> None:
        self.context = context

    def build(self) -> Plan:
        return Plan(
            context=self.context,
            strategy=build_strategy(self.context),
            expected_inputs=collect_expected_inputs(self.context),
            claim_summary=summarize_claim(self.context),
            grounding_notes=_summarize_grounding(self.context.grounding),
            issue_context_notes=_summarize_issue_context(self.context.issue_context),
            observables=_collect_observables(self.context),
            fixture_notes=_collect_fixture_notes(self.context.fixtures),
            preconditions=_collect_preconditions(self.context),
            fallback_strategies=_collect_fallbacks(self.context),
        )


PLAYBOOKS = {
    "signature_check": {
        "preconditions": [
            "⚠️ CRITICAL: The specified target module failed signature checks!",
            "The symbols you need are NOT in the originally specified module.",
            "You MUST use different imports than what the target module suggests.",
        ],
        "fallbacks": [
            "IGNORE the 'Target module' field - it's incorrect for this instance.",
            "Look at the issue's code blocks - copy the EXACT imports shown there.",
            "Use package-level imports: 'import package' then 'package.Symbol'",
            "For sympy: Use 'from sympy import Symbol' instead of 'from sympy.core.X import Symbol'",
            "For pytest: Use 'import pytest' instead of deep module paths",
            "Check test_patch files for working import patterns.",
        ],
        "observables": [
            "Your test imports MUST match the issue's code examples exactly.",
        ],
        "fixtures": [],
    },
    "import_check_failed": {
        "preconditions": [
            "Module import failed in planning phase - this may be OK.",
            "The actual test will run in the correct environment.",
        ],
        "fallbacks": [
            "Use imports shown in the issue's code examples.",
            "Try simpler import paths: 'import package' vs 'from package.sub import Thing'",
            "The module may require the repo environment to import.",
        ],
        "observables": [],
        "fixtures": [],
    },
    "import_error": {
        "preconditions": ["Ensure module import path mirrors repo layout.", "Add sys.path adjustments if needed."],
        "fallbacks": ["Try relative imports or package-qualified names."],
        "observables": [],
        "fixtures": [],
    },
    "internal_import_error": {
        "preconditions": [
            "NEVER import from internal/private modules (_pytest.*, _internal.*, etc.).",
            "Use ONLY public APIs and pytest's built-in fixtures.",
            "Fixtures are declared as function parameters, not imported or accessed as attributes.",
        ],
        "fallbacks": [
            "Check the repo's test files for import and fixture usage examples.",
            "Use fixtures by adding them as test function parameters.",
            "For pytest: tmpdir, tmp_path, tmpdir_factory, monkeypatch, capsys, capfd, etc.",
            "Access fixtures directly in test body after declaring as parameter.",
        ],
        "fixtures": [
            "Fixtures are NOT imported - they're injected as function parameters.",
            "Add fixture names directly to your test function signature.",
            "Example: def test(tmpdir_factory): tmpdir_factory.mktemp('name')",
        ],
    },
    "signature_mismatch": {
        "preconditions": ["Double-check required positional args from signatures."],
        "fallbacks": ["Call helper with dummy data derived from claim GIVEN/WHEN.", "Wrap args in numpy arrays if expected."],
    },
    "fixture_missing": {
        "preconditions": [
            "DO NOT use repo-specific fixtures - they are not available in isolation.",
            "Only use standard pytest fixtures: tmp_path, monkeypatch, capsys, capfd."
        ],
        "fallbacks": [
            "Create objects directly: from module import Class; obj = Class(); obj.method()",
            "Write a helper function inside the test file if setup is complex.",
            "Use monkeypatch to modify module-level state if needed."
        ],
    },
    "assertion_failure": {
        "preconditions": ["Explicitly assert on behavior described in THEN clause."],
        "fallbacks": ["Capture both bug/gold outputs and compare shapes/types before values."],
    },
    "non_discriminative": {
        "preconditions": ["Ensure observable differentiates bug vs gold."],
        "fallbacks": ["Switch to CLI reproduction or compare exception types."],
    },
    "environment_error": {
        "preconditions": [
            "Test code is correct - this is an environment/container issue.",
            "Do NOT modify the test - it's already using correct patterns.",
        ],
        "fallbacks": [
            "The test environment is broken, not the test code.",
            "No code changes will fix this - the container needs to be rebuilt.",
        ],
    },
}


class DynamicPlanner:
    def refine(self, plan: Plan, diagnosis: Optional[Diagnosis]) -> Plan:
        refined = _clone_plan(plan)
        if not diagnosis:
            return refined
        playbook = PLAYBOOKS.get(diagnosis.label)
        if not playbook:
            return refined
        _extend_unique(refined.preconditions, playbook.get("preconditions", []))
        _extend_unique(refined.fallback_strategies, playbook.get("fallbacks", []))
        _extend_unique(refined.observables, playbook.get("observables", []))
        extra_fixture_notes = playbook.get("fixtures", [])
        if extra_fixture_notes:
            _extend_unique(refined.fixture_notes, extra_fixture_notes)
        return refined


def _clone_plan(plan: Plan) -> Plan:
    return Plan(
        context=plan.context,
        strategy=plan.strategy,
        expected_inputs=plan.expected_inputs,
        claim_summary=plan.claim_summary,
        grounding_notes=plan.grounding_notes,
        issue_context_notes=plan.issue_context_notes,
        observables=list(plan.observables),
        fixture_notes=list(plan.fixture_notes),
        preconditions=list(plan.preconditions),
        fallback_strategies=list(plan.fallback_strategies),
    )


def _extend_unique(target: List[str], additions: List[str]) -> None:
    existing = set(target)
    for item in additions:
        if item not in existing:
            target.append(item)
            existing.add(item)


def plan_to_messages(
    plan: Plan,
    guardrail_context: Optional[Dict[str, Any]] = None,
    previous_feedback: Optional[str] = None,
) -> List[Dict[str, str]]:
    # Check if previous feedback indicates a signature_check failure
    # If so, we should de-emphasize the target module that failed
    has_signature_failure = previous_feedback and "SIGNATURE CHECK FAILED" in previous_feedback

    lines = [
        f"Plan for {plan.instance_id}:{plan.claim_id}",
        f"Repository: {plan.repo}",
    ]

    # Handle target module differently based on whether signature check failed
    if has_signature_failure:
        lines.append(f"Original target module (FAILED signature check): {plan.primary_module or 'unknown'}")
        lines.append(f"⚠️ IMPORTANT: The module above failed signature checks - try alternative imports!")
    else:
        lines.append(f"Target module: {plan.primary_module or 'unknown'}")

    lines.extend([
        f"Target symbols: {', '.join(plan.target_symbols) or 'unspecified'}",
        f"Strategy: {plan.strategy}",
        plan.expected_inputs,
        f"Claim summary: {plan.claim_summary}",
    ])
    if plan.observables:
        obs_lines = "\n".join(f"- {item}" for item in plan.observables)
        lines.append(f"Observables:\n{obs_lines}")
    if plan.fixture_notes:
        fixture_lines = "\n".join(f"- {item}" for item in plan.fixture_notes)
        lines.append(f"Fixtures:\n{fixture_lines}")
    if plan.preconditions:
        pre_lines = "\n".join(f"- {item}" for item in plan.preconditions)
        lines.append(f"Preconditions:\n{pre_lines}")
    if plan.fallback_strategies:
        fallback_lines = "\n".join(f"- {item}" for item in plan.fallback_strategies)
        lines.append(f"Fallback strategies:\n{fallback_lines}")
    if plan.grounding_notes:
        lines.append(plan.grounding_notes)
    if plan.issue_context_notes:
        lines.append(plan.issue_context_notes)
    if guardrail_context:
        lines.append(f"Guardrail context: {guardrail_context}")
    if previous_feedback:
        lines.append(f"Previous failure diagnosis: {previous_feedback}")
    user_prompt = "\n".join(lines)
    return [{"role": "user", "content": user_prompt}]
