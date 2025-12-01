"""Verification rules package."""

from .base import RuleImplementation, RuleResult, default_result

RULE_IDS = [f"rule_{i}" for i in range(1, 10)]

__all__ = ["RuleImplementation", "RuleResult", "default_result", "RULE_IDS"]
