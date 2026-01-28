# claim_extraction/pipeline/evidence.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from claim_extraction.pipeline.grounding import normalize_symbol


def verify_evidence_expanded(
    claim: Dict[str, Any],
    problem_statement: str,
    code_context: str,
    stacktrace_info: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Evidence verification against:
      +2 direct span match in issue
      +1 partial match in issue (>= 0.8 token overlap)
      +1 span match in docstring/comment
      +1 stacktrace file+function match (function name matches target symbol variants)
    Score capped at 3.

    Returns:
      {score:int, matches:[...], verified:bool}
    """
    evidence_spans = (claim.get("evidence", {}) or {}).get("spans", []) or []
    target_symbols = claim.get("target_symbols", []) or []

    ps = problem_statement or ""
    ps_lower = ps.lower()

    total_score = 0
    matches: List[Dict[str, Any]] = []

    # --- Issue checks
    for span in evidence_spans:
        if not span or len(span) < 5:
            continue
        span_lower = span.lower()

        if span_lower in ps_lower:
            total_score += 2
            matches.append({"source": "issue", "type": "direct", "span": span[:80]})
            continue

        span_words = set(span_lower.split())
        if len(span_words) >= 3:
            issue_words = set(ps_lower.split())
            overlap = len(span_words & issue_words) / max(1, len(span_words))
            if overlap >= 0.8:
                total_score += 1
                matches.append({"source": "issue", "type": "partial", "overlap": f"{overlap:.0%}", "span": span[:80]})
                continue

    # --- Docstring/comment check (+1 max)
    if code_context:
        doc_pat = r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|#[^\n]+'
        docs_comments = re.findall(doc_pat, code_context)
        docs_text = " ".join(docs_comments).lower()

        for span in evidence_spans:
            if span and len(span) >= 5 and span.lower() in docs_text:
                total_score += 1
                matches.append({"source": "docstring_comment", "type": "direct", "span": span[:80]})
                break

    # --- Stacktrace match (+1 max)
    if stacktrace_info:
        for st in stacktrace_info:
            st_func = st.get("function") or ""
            if not st_func:
                continue

            for sym in target_symbols:
                for v in normalize_symbol(sym):
                    if v.lower() == st_func.lower():
                        total_score += 1
                        matches.append({
                            "source": "stacktrace",
                            "type": "function_match",
                            "stacktrace_func": st_func,
                            "symbol": sym,
                        })
                        break
                if matches and matches[-1].get("source") == "stacktrace":
                    break

            if matches and matches[-1].get("source") == "stacktrace":
                break

    total_score_capped = min(total_score, 3)

    return {
        "score": total_score_capped,
        "matches": matches,
        "verified": total_score_capped > 0,
    }
