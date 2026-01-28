# claim_extraction/pipeline/eligibility.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any

from claim_extraction.constants import (
    ELIGIBILITY_EXCEPTION_KEYWORDS,
    ELIGIBILITY_BEHAVIOR_KEYWORDS,
)

@dataclass
class EligibilityResult:
    eligible: bool
    score: int
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"eligible": self.eligible, "score": self.score, "reasons": self.reasons}


_STACKTRACE_RE = re.compile(r'File ["\'].+?["\'], line \d+')

def check_issue_eligibility(problem_statement: str, *, threshold: int = 2) -> EligibilityResult:
    """
    Eligibility scoring (deterministic):
    +2 mentions concrete exception keyword (ValueError, TypeError, ...)
    +2 stacktrace present (Traceback or File "...", line N)
    +1 behavioral keyword (should return, fails to, ...)
    +1 code refs via backticks
    +1 code refs via func()
    +1 code blocks (``` or >>>)

    Eligible if score >= threshold
    """
    ps = problem_statement or ""
    ps_lower = ps.lower()

    reasons: List[str] = []
    score = 0

    # exception keyword (case-sensitive match)
    for exc in ELIGIBILITY_EXCEPTION_KEYWORDS:
        if exc in ps:
            reasons.append(f"mentions_exception:{exc}")
            score += 2
            break

    # stacktrace
    if ("Traceback" in ps) or _STACKTRACE_RE.search(ps):
        reasons.append("has_stacktrace")
        score += 2

    # behavioral keywords
    for kw in ELIGIBILITY_BEHAVIOR_KEYWORDS:
        if kw in ps_lower:
            reasons.append(f"behavior_keyword:{kw}")
            score += 1
            break

    # code refs
    if "`" in ps:
        reasons.append("has_code_refs")
        score += 1

    if re.search(r"\w+\(\)", ps):
        reasons.append("has_func_refs")
        score += 1

    # code blocks
    if "```" in ps or ">>>" in ps:
        reasons.append("has_code_examples")
        score += 1

    eligible = score >= threshold
    if not eligible and score == 0 and any(w in ps_lower for w in ("doesn't work", "does not work", "broken")):
        reasons.append("vague_only")

    return EligibilityResult(eligible=eligible, score=score, reasons=reasons)
