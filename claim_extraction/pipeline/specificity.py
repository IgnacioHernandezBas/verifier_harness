# claim_extraction/pipeline/specificity.py
from __future__ import annotations

from typing import Any, Dict, List

from claim_extraction.constants import OBSERVABLE_KEYWORDS


def compute_claim_specificity(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    A claim is specific if:
      - has non-empty target_symbols
      - THEN contains observable keyword
      - not vague language
      - given/when are reasonably concrete
    """
    target_symbols = claim.get("target_symbols", []) or []
    then_text = (claim.get("then", "") or "").lower()
    given_text = (claim.get("given", "") or "").lower()
    when_text = (claim.get("when", "") or "").lower()

    issues: List[str] = []

    # symbols
    has_symbols = bool(target_symbols) and all(isinstance(s, str) and len(s.strip()) > 1 for s in target_symbols)
    if not has_symbols:
        issues.append("empty_or_trivial_symbols")

    # observable
    has_observable = any(obs in then_text for obs in OBSERVABLE_KEYWORDS)
    if not has_observable:
        issues.append("no_observable_in_then")

    # vague language
    vague_phrases = ["properly", "correctly", "should work", "as expected", "handle"]
    if any(vp in then_text or vp in given_text for vp in vague_phrases):
        issues.append("vague_language")

    # concrete given/when heuristics
    has_concrete_given = len(given_text) > 10 and not given_text.startswith("a ")
    has_concrete_when = len(when_text) > 10
    if not has_concrete_given:
        issues.append("vague_given")
    if not has_concrete_when:
        issues.append("vague_when")

    return {
        "is_specific": len(issues) == 0,
        "issues": issues,
        "has_symbols": has_symbols,
        "has_observable": has_observable,
    }
