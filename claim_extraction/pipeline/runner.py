# claim_extraction/pipeline/runner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from claim_extraction.llm.base import LLMClient
from claim_extraction.parsing.json_repair import parse_json_array_with_fallbacks
from claim_extraction.pipeline.eligibility import check_issue_eligibility
from claim_extraction.pipeline.grounding import calculate_grounding_strength
from claim_extraction.pipeline.stacktrace import extract_stacktrace_info
from claim_extraction.pipeline.evidence import verify_evidence_expanded
from claim_extraction.pipeline.scoring import compute_claim_score_v2
from claim_extraction.pipeline.specificity import compute_claim_specificity
from claim_extraction.pipeline.issue_context import (
    build_issue_context,
    link_claim_to_issue_context,
)


@dataclass
class InstanceResult:
    instance_id: str
    repo: Optional[str]
    eligible: bool
    eligibility: Dict[str, Any]
    claims: List[Dict[str, Any]]
    ungrounded_claims: List[Dict[str, Any]]
    low_score_claims: List[Dict[str, Any]]
    extraction_details: Dict[str, Any]
    stats: Dict[str, Any]
    schema_version: Optional[str] = None
    issue_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "instance_id": self.instance_id,
            "repo": self.repo,
            "eligible": self.eligible,
            "eligibility": self.eligibility,
            "claims": self.claims,
            "ungrounded_claims": self.ungrounded_claims,
            "low_score_claims": self.low_score_claims,
            "extraction_details": self.extraction_details,
            "stats": self.stats,
        }
        if self.schema_version is not None:
            data["schema_version"] = self.schema_version
        if self.issue_context is not None:
            data["issue_context"] = self.issue_context
        return data


def build_prompt_env() -> Environment:
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    return Environment(loader=FileSystemLoader(str(prompts_dir)), autoescape=False)


def _ensure_list_symbols(claim: Dict[str, Any]) -> None:
    ts = claim.get("target_symbols")
    if isinstance(ts, str):
        claim["target_symbols"] = [ts]
    elif ts is None:
        claim["target_symbols"] = []
    elif not isinstance(ts, list):
        claim["target_symbols"] = []


def _normalize_confidence(claim: Dict[str, Any]) -> None:
    c = str(claim.get("confidence", "medium")).lower()
    if c not in ("high", "medium", "low"):
        c = "medium"
    claim["confidence"] = c


def _validate_min_structure(claim: Dict[str, Any]) -> Optional[str]:
    required = ["claim_id", "claim_type", "claim_text", "target_symbols", "confidence"]
    for f in required:
        if f not in claim:
            return f"missing_{f}"
    if claim.get("claim_type") not in ("return", "exception", "invariant", "state_change"):
        return "invalid_claim_type"
    if not isinstance(claim.get("target_symbols"), list):
        return "invalid_target_symbols"
    if len(claim.get("target_symbols", [])) == 0:
        return "empty_target_symbols"
    return None


def process_instance(
    instance: Dict[str, Any],
    *,
    cfg: Dict[str, Any],
    llm: LLMClient,
    prompt_env: Environment,
    template_name: str = "claim_prompt_v2_1.jinja",
    touched_files_text: Optional[Dict[str, str]] = None,
) -> InstanceResult:
    instance_id = instance.get("instance_id") or instance.get("metadata", {}).get("instance_id", "unknown")
    repo = instance.get("repo")
    problem_statement = instance.get("problem_statement", "") or ""
    code_context = instance.get("code_context", "") or ""
    patch = instance.get("patch", "") or ""
    schema_version = str(cfg.get("schema_version", "2.1"))
    issue_context_enabled = schema_version == "2.2"
    issue_context = build_issue_context(problem_statement) if issue_context_enabled else None

    # 1) eligibility
    threshold = int(cfg.get("eligibility", {}).get("threshold", 2))
    eligibility = check_issue_eligibility(problem_statement, threshold=threshold)
    check_elig = bool(cfg.get("extraction", {}).get("check_eligibility", True))
    if check_elig and not eligibility.eligible:
        return InstanceResult(
            instance_id=instance_id,
            repo=repo,
            eligible=False,
            eligibility=eligibility.to_dict(),
            claims=[],
            ungrounded_claims=[],
            low_score_claims=[],
            extraction_details={"parse_details": {"attempts": [{"method": "skipped_ineligible", "success": True}]}},
            stats={"eligible": False},
            schema_version=schema_version if issue_context_enabled else None,
            issue_context=issue_context,
        )

    # 2) stacktrace info (for evidence)
    stacktrace_info = extract_stacktrace_info(problem_statement)

    # 3) prompt render
    tmpl = prompt_env.get_template(template_name)
    max_chars = int(cfg.get("context", {}).get("max_chars", 22000))
    code_ctx_trim = code_context[:max_chars]
    prompt = tmpl.render(problem_statement=problem_statement, code_context=code_ctx_trim)

    # 4) LLM call
    llm_cfg = cfg.get("llm", {})
    resp = llm.generate(
        prompt,
        temperature=float(llm_cfg.get("temperature", 0.0)),
        max_tokens=int(llm_cfg.get("max_tokens", 2048)),
        stop=None,
    )

    # 5) parse
    raw_claims, parse_details = parse_json_array_with_fallbacks(resp.text)

    # 6) validate/normalize
    validated: List[Dict[str, Any]] = []
    validation_errors: List[Dict[str, Any]] = []

    for c in raw_claims:
        if not isinstance(c, dict):
            continue
        _ensure_list_symbols(c)
        _normalize_confidence(c)
        err = _validate_min_structure(c)
        if err:
            validation_errors.append({"claim_id": c.get("claim_id"), "error": err})
            continue
        validated.append(c)

    if issue_context is not None:
        for c in validated:
            c["issue_context_refs"] = link_claim_to_issue_context(c, issue_context)

    # 7) grounding + evidence + scoring + specificity
    require_grounding = bool(cfg.get("extraction", {}).get("require_grounding", True))
    min_score = int(cfg.get("extraction", {}).get("min_claim_score", 2))

    grounded: List[Dict[str, Any]] = []
    ungrounded: List[Dict[str, Any]] = []
    low_score: List[Dict[str, Any]] = []

    final_claims: List[Dict[str, Any]] = []

    for c in validated:
        # grounding (v2.1)
        gr = calculate_grounding_strength(
            c, patch,
            touched_files_text=touched_files_text,
            code_context=code_context,
        )
        c["grounding"] = gr.to_dict()

        if gr.status == "none":
            ungrounded.append(c)
            if require_grounding:
                continue  # discard if grounding required

        if gr.status != "none":
            grounded.append(c)

        # evidence verification expanded
        ev = verify_evidence_expanded(c, problem_statement, code_context, stacktrace_info)
        c["evidence_verification"] = ev

        # scoring v2.1
        scoring = compute_claim_score_v2(c, ev)
        c["computed_score"] = scoring["score"]
        c["score_factors"] = scoring["factors"]

        # specificity
        spec = compute_claim_specificity(c)
        c["specificity"] = spec

        if c["computed_score"] >= min_score:
            final_claims.append(c)
        else:
            low_score.append(c)

    final_claims.sort(key=lambda x: int(x.get("computed_score", 0)), reverse=True)

    # 8) stats
    by_grounding = {
        "strong": sum(1 for c in final_claims if c.get("grounding", {}).get("status") == "strong"),
        "weak_file": sum(1 for c in final_claims if c.get("grounding", {}).get("status") == "weak_file"),
        "weak_ref": sum(1 for c in final_claims if c.get("grounding", {}).get("status") == "weak_ref"),
    }
    by_confidence = {
        "high": sum(1 for c in final_claims if c.get("confidence") == "high"),
        "medium": sum(1 for c in final_claims if c.get("confidence") == "medium"),
        "low": sum(1 for c in final_claims if c.get("confidence") == "low"),
    }

    specificity_rate = (sum(1 for c in final_claims if c.get("specificity", {}).get("is_specific")) / len(final_claims)) if final_claims else 0.0
    evidence_verified_rate = (sum(1 for c in final_claims if c.get("evidence_verification", {}).get("verified")) / len(final_claims)) if final_claims else 0.0
    avg_score = (sum(int(c.get("computed_score", 0)) for c in final_claims) / len(final_claims)) if final_claims else 0.0

    stats = {
        "eligible": True,
        "eligibility_score": eligibility.score,
        "raw_claims": len(raw_claims),
        "validated_claims": len(validated),
        "validation_errors": validation_errors,
        "grounded_claims": len(grounded),
        "ungrounded_claims": len(ungrounded),
        "final_claims": len(final_claims),
        "grounding_rate": (len(grounded) / len(validated)) if validated else 0.0,
        "by_grounding": by_grounding,
        "by_confidence": by_confidence,
        "specificity_rate": specificity_rate,
        "evidence_verified_rate": evidence_verified_rate,
        "avg_score": avg_score,
        "parse_details": parse_details,
    }

    extraction_details = {
        "parse_details": parse_details,
        "raw_claims": len(raw_claims),
        "validated_claims": len(validated),
        "validation_errors": validation_errors,
    }

    return InstanceResult(
        instance_id=instance_id,
        repo=repo,
        eligible=True,
        eligibility=eligibility.to_dict(),
        claims=final_claims,
        ungrounded_claims=ungrounded,
        low_score_claims=low_score,
        extraction_details=extraction_details,
        stats=stats,
        schema_version=schema_version if issue_context_enabled else None,
        issue_context=issue_context,
    )
