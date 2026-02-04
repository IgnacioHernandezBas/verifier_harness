# claim_extraction/cli.py
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

from claim_extraction.config import load_config
from claim_extraction.llm.factory import build_llm_client
from claim_extraction.pipeline.runner import build_prompt_env, process_instance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("claim_extraction.cli")


def _load_instances(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    # supports either list[...] or {"instances": [...]} or {"id": {...}, ...}
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "instances" in data and isinstance(data["instances"], list):
            return data["instances"]
        # dict-of-dicts -> values
        if all(isinstance(v, dict) for v in data.values()):
            return list(data.values())
    raise ValueError("Unsupported instances.json format. Expected list or dict with 'instances'.")


def _safe_instance_id(inst: Dict[str, Any]) -> str:
    return inst.get("instance_id") or inst.get("metadata", {}).get("instance_id") or "unknown"


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _aggregate_summary(results: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
    eligible = [r for r in results if r.get("eligible")]

    total_raw = sum((r.get("stats", {}) or {}).get("raw_claims", 0) for r in eligible)
    total_grounded = sum((r.get("stats", {}) or {}).get("grounded_claims", 0) for r in eligible)
    total_final = sum((r.get("stats", {}) or {}).get("final_claims", 0) for r in eligible)

    by_grounding = {
        "strong": sum(((r.get("stats", {}) or {}).get("by_grounding", {}) or {}).get("strong", 0) for r in eligible),
        "weak_file": sum(((r.get("stats", {}) or {}).get("by_grounding", {}) or {}).get("weak_file", 0) for r in eligible),
        "weak_ref": sum(((r.get("stats", {}) or {}).get("by_grounding", {}) or {}).get("weak_ref", 0) for r in eligible),
    }

    def _avg(metric: str) -> float:
        vals = [float((r.get("stats", {}) or {}).get(metric, 0.0)) for r in eligible]
        return sum(vals) / len(vals) if vals else 0.0

    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "llm": cfg.get("llm", {}),
            "extraction": cfg.get("extraction", {}),
        },
        "eligibility": {
            "total_instances": len(results),
            "eligible": len(eligible),
            "ineligible": len(results) - len(eligible),
            "eligibility_rate": (len(eligible) / len(results)) if results else 0.0,
        },
        "totals": {
            "total_raw_claims": total_raw,
            "total_grounded_claims": total_grounded,
            "total_final_claims": total_final,
            "avg_final_claims_per_eligible_instance": (total_final / len(eligible)) if eligible else 0.0,
            "grounding_rate": (total_grounded / total_raw) if total_raw else 0.0,
        },
        "by_grounding": by_grounding,
        "quality_metrics": {
            "avg_specificity_rate": _avg("specificity_rate"),
            "avg_evidence_verified_rate": _avg("evidence_verified_rate"),
            "avg_claim_score": _avg("avg_score"),
        },
        "instances": [
            {
                "instance_id": r.get("instance_id"),
                "repo": r.get("repo"),
                "eligible": r.get("eligible"),
                "final_claims": (r.get("stats", {}) or {}).get("final_claims", 0),
                "grounding_rate": (r.get("stats", {}) or {}).get("grounding_rate", 0.0),
                "avg_score": (r.get("stats", {}) or {}).get("avg_score", 0.0),
                "specificity_rate": (r.get("stats", {}) or {}).get("specificity_rate", 0.0),
            }
            for r in results
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="Claim Extractor (modular) v2.1")
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--input", required=True, help="instances.json (list or dict format)")
    ap.add_argument("--out", required=True, help="Output directory")

    ap.add_argument("--limit", type=int, default=None, help="Limit number of instances")
    ap.add_argument("--min-score", type=int, default=None, help="Override extraction.min_claim_score")
    ap.add_argument("--skip-eligibility", action="store_true", help="Disable eligibility filter")
    ap.add_argument("--require-grounding", dest="require_grounding", action="store_true", help="Require grounding (default)")
    ap.add_argument("--no-require-grounding", dest="require_grounding", action="store_false", help="Do not require grounding")
    ap.set_defaults(require_grounding=None)

    ap.add_argument("--dry-run", action="store_true", help="Render prompts and exit (no LLM calls)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    template_name = cfg.get("prompt_template", "claim_prompt_v2_1.jinja")

    # CLI overrides -> config
    cfg.setdefault("extraction", {})
    if args.min_score is not None:
        cfg["extraction"]["min_claim_score"] = int(args.min_score)
    if args.skip_eligibility:
        cfg["extraction"]["check_eligibility"] = False
    if args.require_grounding is not None:
        cfg["extraction"]["require_grounding"] = bool(args.require_grounding)

    input_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    instances = _load_instances(input_path)
    if args.limit is not None:
        instances = instances[: args.limit]

    logger.info(f"Loaded {len(instances)} instances from {input_path}")

    prompt_env = build_prompt_env()

    if args.dry_run:
        # write first prompt to inspect
        from jinja2 import TemplateNotFound
        tmpl = prompt_env.get_template(template_name)
        if instances:
            inst = instances[0]
            ps = inst.get("problem_statement", "") or ""
            cc = inst.get("code_context", "") or ""
            prompt = tmpl.render(problem_statement=ps, code_context=cc)
            (out_dir / "dry_run_prompt.txt").write_text(prompt, encoding="utf-8")
            logger.info(f"Dry-run wrote prompt to {out_dir / 'dry_run_prompt.txt'}")
        return

    llm = build_llm_client(cfg["llm"])

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for idx, inst in enumerate(instances, start=1):
        iid = _safe_instance_id(inst)
        logger.info(f"[{idx}/{len(instances)}] Processing {iid}")

        try:
            res_obj = process_instance(
                inst,
                cfg=cfg,
                llm=llm,
                prompt_env=prompt_env,
                template_name=template_name,
                touched_files_text=inst.get("touched_files_text"),
            )
            res = res_obj.to_dict()
            results.append(res)

            _write_json(out_dir / f"{iid}.json", res)

            if res.get("eligible"):
                st = res.get("stats", {}) or {}
                logger.info(
                    f"  eligible | raw={st.get('raw_claims')} | grounded={st.get('grounded_claims')} | final={st.get('final_claims')} | avg_score={st.get('avg_score'):.2f}"
                )
            else:
                logger.info("  ineligible")

        except Exception as e:
            logger.exception(f"Error processing {iid}: {e}")
            errors.append({"instance_id": iid, "error": str(e)})

    summary = _aggregate_summary(results, cfg)
    summary["errors"] = errors
    _write_json(out_dir / "summary.json", summary)

    logger.info("==============================================")
    logger.info("EXTRACTION SUMMARY")
    logger.info("==============================================")
    logger.info(f"Output dir: {out_dir}")
    logger.info(f"Total: {len(results)} | Errors: {len(errors)}")
    logger.info(
        f"Eligibility: {summary['eligibility']['eligible']}/{summary['eligibility']['total_instances']} ({summary['eligibility']['eligibility_rate']:.1%})"
    )
    logger.info(
        f"Totals: raw={summary['totals']['total_raw_claims']} grounded={summary['totals']['total_grounded_claims']} final={summary['totals']['total_final_claims']}"
    )
    logger.info(f"By grounding: {summary['by_grounding']}")
    logger.info(
        f"Quality: specificity={summary['quality_metrics']['avg_specificity_rate']:.1%}, evidence={summary['quality_metrics']['avg_evidence_verified_rate']:.1%}, avg_score={summary['quality_metrics']['avg_claim_score']:.2f}"
    )


if __name__ == "__main__":
    main()
