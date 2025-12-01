"""Shared types and helpers for verification rules."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Protocol


RuleStatus = str


@dataclass
class RuleResult:
    """Structured result produced by every rule."""

    rule_id: str
    name: str
    status: RuleStatus
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    details: str = ""

    def add_finding(self, description: str, location: str = "", severity: str = "medium", taxonomy_tags: List[str] | None = None) -> None:
        """Append a finding and mark the rule as failed."""
        taxonomy = taxonomy_tags or []
        self.findings.append(
            {
                "description": description,
                "location": location,
                "severity": severity,
                "taxonomy_tags": taxonomy,
            }
        )
        if self.status == "passed":
            self.status = "failed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dictionary for JSON output."""
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


class RuleImplementation(Protocol):
    """Protocol for rule entrypoints."""

    def run_rule(self, repo_path: str, patch_str: str, **kwargs: Any) -> RuleResult:
        ...


def default_result(rule_id: str, name: str) -> RuleResult:
    """Create a passing result shell with metadata."""
    return RuleResult(rule_id=rule_id, name=name, status="passed")
