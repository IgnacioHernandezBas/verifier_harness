# claim_extraction/pipeline/scoring.py
from __future__ import annotations

from typing import Any, Dict, List

from claim_extraction.constants import OBSERVABLE_KEYWORDS


def compute_claim_score_v2(
    claim: Dict[str, Any],
    evidence_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Composite scoring (v2.1):
      +3 strong grounding
      +1 weak grounding (file or ref)
      +0 none

      +evidence_score (0-3): expanded evidence verification
      +1 has observable
      -1 no observable

      confidence: high +1, medium +0, low -1
    """
    score = 0
    factors: List[str] = []

    grounding = claim.get("grounding", {}) or {}
    g_status = grounding.get("status", "none")

    # grounding points
    if g_status == "strong":
        score += 3
        factors.append("+3: strong_grounding (defined/assigned symbol in diff)")
    elif g_status in ("weak_file", "weak_ref"):
        score += 1
        factors.append(f"+1: {g_status}")
    else:
        factors.append("+0: no_grounding")

    # evidence points
    ev_score = int(evidence_result.get("score", 0))
    if ev_score > 0:
        score += ev_score
        sources = {m.get("source") for m in evidence_result.get("matches", [])}
        sources = {s for s in sources if s}
        factors.append(f"+{ev_score}: evidence_verified ({', '.join(sorted(sources))})")
    else:
        factors.append("+0: evidence_not_verified")

    # observable (+1 / -1)
    claim_text = (claim.get("claim_text", "") or "").lower()
    then_text = (claim.get("then", "") or "").lower()
    combined = f"{claim_text} {then_text}"
    has_observable = any(obs in combined for obs in OBSERVABLE_KEYWORDS)

    if has_observable:
        score += 1
        factors.append("+1: has_observable")
    else:
        score -= 1
        factors.append("-1: no_observable")

    # confidence
    conf = (claim.get("confidence", "medium") or "medium").lower()
    if conf == "high":
        score += 1
        factors.append("+1: high_confidence")
    elif conf == "low":
        score -= 1
        factors.append("-1: low_confidence")
    else:
        factors.append("+0: medium_confidence")

    return {
        "score": score,
        "factors": factors,
        "grounding_status": g_status,
        "evidence_verified": bool(evidence_result.get("verified", False)),
        "has_observable": has_observable,
    }
