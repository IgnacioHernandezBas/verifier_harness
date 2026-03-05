"""
Multi-Layer Verification Harness
=================================

Interconnects three verification layers into a single, composable pipeline
that users can run against agent-generated patches:

    Layer 1  --  Static Analysis   (pylint, flake8, radon, mypy, bandit, AST)
    Layer 2  --  Unit-Test Exec    (pytest inside Singularity / Podman containers)
    Layer 3  --  Claim-Test Gen    (LLM-driven claim extraction -> test generation -> BUG/GOLD verification)

Each layer produces a typed ``LayerResult`` and the harness aggregates them
into a ``HarnessReport`` with a final ACCEPT / REJECT / WARNING verdict.

Usage (programmatic)::

    harness = MultiLayerHarness(config)
    report  = harness.run(patch_data)
    print(report.verdict, report.reason)

Usage (CLI)::

    python -m verifier.multi_layer_harness \\
        --instance django__django-12345 \\
        --patch-file patch.diff \\
        --repo-path /tmp/repos/django \\
        --layers static unit_test claim_test
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Verdict enum
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SKIP = "SKIP"


# ---------------------------------------------------------------------------
# Per-layer result
# ---------------------------------------------------------------------------

@dataclass
class LayerResult:
    """Result produced by a single verification layer."""

    layer: str
    verdict: str
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Aggregated report
# ---------------------------------------------------------------------------

@dataclass
class HarnessReport:
    """Aggregated report across all layers."""

    instance_id: str
    verdict: str = Verdict.ACCEPT.value
    reason: str = ""
    layers: List[LayerResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    total_duration_s: float = 0.0

    # Convenience helpers ------------------------------------------------

    def layer_by_name(self, name: str) -> Optional[LayerResult]:
        for lr in self.layers:
            if lr.layer == name:
                return lr
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "verdict": self.verdict,
            "reason": self.reason,
            "layers": [lr.to_dict() for lr in self.layers],
            "timestamp": self.timestamp,
            "total_duration_s": self.total_duration_s,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Default harness configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    # Which layers to enable by default
    "layers": ["static", "unit_test", "claim_test"],

    # Static layer
    "static": {
        "sqi_threshold": 0.5,
        "fail_on_syntax_error": True,
    },

    # Unit-test execution layer
    "unit_test": {
        "timeout_s": 300,
        "coverage_threshold": 0.0,
        "fail_on_test_failure": True,
    },

    # Claim-test layer
    "claim_test": {
        "timeout_s": 300,
        "cvr_threshold": 0.0,
        "max_claims": None,
        "use_container": True,
    },

    # Supplementary rules (optional, bolted onto static layer)
    "rules": {
        "enabled": True,
        "fail_on_high_severity": True,
    },

    # Verdict aggregation policy
    "aggregation": {
        # "all_pass"  - all layers must ACCEPT
        # "majority"  - majority of layers must ACCEPT
        # "any_pass"  - at least one layer must ACCEPT
        "policy": "all_pass",
    },
}


def _merge_config(base: Dict, overrides: Optional[Dict]) -> Dict:
    """Shallow-merge *overrides* into a copy of *base* (one level deep)."""
    merged = {}
    for key, val in base.items():
        if isinstance(val, dict) and isinstance(overrides.get(key) if overrides else None, dict):
            merged[key] = {**val, **overrides[key]}  # type: ignore[index]
        elif overrides and key in overrides:
            merged[key] = overrides[key]
        else:
            merged[key] = val
    return merged


# ---------------------------------------------------------------------------
# Multi-Layer Harness
# ---------------------------------------------------------------------------

class MultiLayerHarness:
    """
    Orchestrates static analysis, unit-test execution, and claim-test
    generation/verification as composable verification layers.

    Parameters
    ----------
    config : dict, optional
        Override any key in ``DEFAULT_CONFIG``.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.cfg = _merge_config(DEFAULT_CONFIG, config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, patch_data: Dict[str, Any]) -> HarnessReport:
        """
        Run all enabled layers against *patch_data* and return an aggregated
        ``HarnessReport``.

        Parameters
        ----------
        patch_data : dict
            Must contain at minimum:
              - ``instance_id`` (str)
              - ``diff`` (str) -- unified diff of the patch

            Optional (required by specific layers):
              - ``repo_path`` (str | Path) -- checked-out repo with patch applied
              - ``sample`` (dict)          -- full SWE-bench sample for claim-test layer
              - ``claim_tests_root`` (str) -- root dir of generated claim tests
              - ``patched_code`` (str)     -- full source after patch (for fuzzing)
              - ``original_code`` (str)    -- full source before patch (for diff testing)
        """
        start = time.time()
        instance_id = (
            patch_data.get("instance_id")
            or patch_data.get("id")
            or "unknown"
        )
        report = HarnessReport(instance_id=instance_id, timestamp=start)

        enabled_layers: List[str] = self.cfg.get("layers", [])

        for layer_name in enabled_layers:
            handler = self._get_layer_handler(layer_name)
            if handler is None:
                logger.warning("Unknown layer %r -- skipping", layer_name)
                continue
            try:
                lr = handler(patch_data)
            except Exception as exc:
                logger.exception("Layer %r raised an exception", layer_name)
                lr = LayerResult(
                    layer=layer_name,
                    verdict=Verdict.ERROR.value,
                    error=f"{type(exc).__name__}: {exc}",
                    duration_s=0.0,
                )
            report.layers.append(lr)

        report.total_duration_s = time.time() - start
        report.verdict, report.reason = self._aggregate(report.layers)
        return report

    # ------------------------------------------------------------------
    # Layer handlers
    # ------------------------------------------------------------------

    def _get_layer_handler(self, name: str):
        return {
            "static": self._run_static_layer,
            "unit_test": self._run_unit_test_layer,
            "claim_test": self._run_claim_test_layer,
        }.get(name)

    # ---- Layer 1: Static Analysis ------------------------------------

    def _run_static_layer(self, patch_data: Dict[str, Any]) -> LayerResult:
        t0 = time.time()
        diff = patch_data.get("diff", "")
        repo_path = patch_data.get("repo_path")
        cfg = self.cfg.get("static", {})

        if not repo_path:
            return LayerResult(
                layer="static",
                verdict=Verdict.SKIP.value,
                error="No repo_path provided -- cannot run static analysis",
                duration_s=time.time() - t0,
            )

        repo_path = str(repo_path)
        findings: List[Dict[str, Any]] = []

        # --- 1a) Code quality (pylint / flake8 / radon / mypy / bandit) ---
        try:
            from verifier.static_analyzers.code_quality import analyze as cq_analyze

            cq_result = cq_analyze(repo_path=repo_path, patch_str=diff)
            sqi_data = cq_result.get("sqi", {})
            sqi_score = sqi_data.get("SQI", 0.0) / 100.0  # normalize to [0,1]
        except Exception as exc:
            logger.warning("Code-quality analysis failed: %s", exc)
            cq_result = {"error": str(exc)}
            sqi_score = 0.0

        # --- 1b) Syntax & structure (AST validation) ---
        try:
            from verifier.static_analyzers.syntax_structure import (
                run_syntax_structure_analysis,
            )

            ss_result = run_syntax_structure_analysis(repo_path=repo_path, diff_text=diff)
            has_syntax_errors = any(
                not fr.get("is_code_valid", True) for fr in ss_result
            )
        except Exception as exc:
            logger.warning("Syntax-structure analysis failed: %s", exc)
            ss_result = [{"error": str(exc)}]
            has_syntax_errors = False

        # --- 1c) Supplementary rules (optional) ---
        rules_result: Optional[Dict[str, Any]] = None
        rules_cfg = self.cfg.get("rules", {})
        if rules_cfg.get("enabled", False):
            try:
                from verifier.rules.runner import run_rules
                from verifier.rules import RULE_IDS

                rule_results = run_rules(
                    rule_ids=RULE_IDS,
                    repo_path=repo_path,
                    patch_str=diff,
                )
                failed_rules = [r for r in rule_results if r.status == "failed"]
                high_sev = [
                    f
                    for r in failed_rules
                    for f in r.findings
                    if f.get("severity") == "high"
                ]
                rules_result = {
                    "total": len(rule_results),
                    "failed": len(failed_rules),
                    "high_severity_findings": len(high_sev),
                    "details": [r.to_dict() for r in rule_results],
                }
                findings.extend(
                    f for r in failed_rules for f in r.findings
                )
            except Exception as exc:
                logger.warning("Supplementary rules failed: %s", exc)
                rules_result = {"error": str(exc)}

        # --- Verdict ---
        verdict = Verdict.ACCEPT.value
        reasons: List[str] = []

        if cfg.get("fail_on_syntax_error", True) and has_syntax_errors:
            verdict = Verdict.REJECT.value
            reasons.append("Syntax errors detected in patched files")

        if sqi_score < cfg.get("sqi_threshold", 0.5):
            if verdict != Verdict.REJECT.value:
                verdict = Verdict.REJECT.value
            reasons.append(f"SQI={sqi_score:.2f} below threshold {cfg.get('sqi_threshold', 0.5)}")

        if (
            rules_result
            and rules_result.get("high_severity_findings", 0) > 0
            and rules_cfg.get("fail_on_high_severity", True)
        ):
            verdict = Verdict.REJECT.value
            reasons.append(
                f"{rules_result['high_severity_findings']} high-severity rule findings"
            )

        if not reasons and verdict == Verdict.ACCEPT.value:
            reasons.append(f"Static checks passed (SQI={sqi_score:.2f})")

        return LayerResult(
            layer="static",
            verdict=verdict,
            score=sqi_score,
            details={
                "code_quality": cq_result,
                "syntax_structure": ss_result,
                "rules": rules_result,
            },
            findings=findings,
            duration_s=time.time() - t0,
        )

    # ---- Layer 2: Unit-Test Execution --------------------------------

    def _run_unit_test_layer(self, patch_data: Dict[str, Any]) -> LayerResult:
        t0 = time.time()
        diff = patch_data.get("diff", "")
        repo_path = patch_data.get("repo_path")
        instance_id = patch_data.get("instance_id") or patch_data.get("id", "unknown")
        cfg = self.cfg.get("unit_test", {})

        if not repo_path:
            return LayerResult(
                layer="unit_test",
                verdict=Verdict.SKIP.value,
                error="No repo_path provided -- cannot execute tests",
                duration_s=time.time() - t0,
            )

        repo_path = Path(repo_path)

        # Try SWE-bench Singularity executor first (preferred for reproducibility)
        try:
            from verifier.dynamic_analyzers.swebench_singularity_executor import (
                SingularitySWEBenchExecutor,
                TestType,
            )

            executor = SingularitySWEBenchExecutor(
                timeout=cfg.get("timeout_s", 300),
            )

            # Run SWE-bench official test suite if eval script is available
            eval_script = patch_data.get("eval_script")
            if eval_script:
                exec_result = executor.run_swebench_tests(
                    instance_id=instance_id,
                    patch_diff=diff,
                    eval_script_path=eval_script,
                )
                tests_passed = exec_result.success
                test_output = {
                    "exit_code": exec_result.exit_code,
                    "stdout": getattr(exec_result, "stdout", "")[:2000],
                    "stderr": getattr(exec_result, "stderr", "")[:2000],
                }
            else:
                # Generate and run Hypothesis fuzzing tests
                tests_passed, test_output = self._run_generated_tests(
                    diff, repo_path, instance_id, executor, cfg
                )

        except ImportError:
            logger.info("Singularity executor not available, trying Podman")
            try:
                from verifier.dynamic_analyzers.podman_executor import (
                    PodmanTestExecutor,
                    IntegratedTestRunner,
                    TestType,
                )

                runner = IntegratedTestRunner()
                exec_result = runner.run_tests(
                    instance_id=instance_id,
                    patch_diff=diff,
                    test_type=TestType.SWEBENCH,
                )
                tests_passed = exec_result.success
                test_output = exec_result.to_dict()

            except Exception as exc:
                return LayerResult(
                    layer="unit_test",
                    verdict=Verdict.ERROR.value,
                    error=f"No container runtime available: {exc}",
                    duration_s=time.time() - t0,
                )

        except Exception as exc:
            return LayerResult(
                layer="unit_test",
                verdict=Verdict.ERROR.value,
                error=f"Test execution failed: {exc}",
                duration_s=time.time() - t0,
            )

        verdict = (
            Verdict.ACCEPT.value
            if tests_passed
            else Verdict.REJECT.value
            if cfg.get("fail_on_test_failure", True)
            else Verdict.WARNING.value
        )

        return LayerResult(
            layer="unit_test",
            verdict=verdict,
            score=1.0 if tests_passed else 0.0,
            details=test_output if isinstance(test_output, dict) else {"output": test_output},
            duration_s=time.time() - t0,
        )

    def _run_generated_tests(self, diff, repo_path, instance_id, executor, cfg):
        """Generate Hypothesis tests from the patch and execute them."""
        from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
        from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator

        analyzer = PatchAnalyzer()
        generator = HypothesisTestGenerator(enable_differential=True)

        patch_analysis = analyzer.parse_patch(diff, "")
        if not patch_analysis.changed_functions:
            return True, {"skipped": True, "reason": "No changed functions detected"}

        test_code = generator.generate_tests(patch_analysis, patched_code="", original_code=None)
        from verifier.dynamic_analyzers.swebench_singularity_executor import TestType

        exec_result = executor.run_custom_tests(
            instance_id=instance_id,
            patch_diff=diff,
            test_code=test_code,
            test_type=TestType.FUZZING,
        )
        return exec_result.success, exec_result.to_dict()

    # ---- Layer 3: Claim-Test Generation & Verification ---------------

    def _run_claim_test_layer(self, patch_data: Dict[str, Any]) -> LayerResult:
        t0 = time.time()
        cfg = self.cfg.get("claim_test", {})

        sample = patch_data.get("sample")
        claim_tests_root = patch_data.get("claim_tests_root")
        instance_id = patch_data.get("instance_id") or patch_data.get("id", "unknown")

        if not sample:
            return LayerResult(
                layer="claim_test",
                verdict=Verdict.SKIP.value,
                error="No 'sample' dict provided -- cannot run claim-test verification",
                duration_s=time.time() - t0,
            )

        if not claim_tests_root:
            return LayerResult(
                layer="claim_test",
                verdict=Verdict.SKIP.value,
                error="No 'claim_tests_root' provided -- cannot locate claim tests",
                duration_s=time.time() - t0,
            )

        try:
            from claim_test_verification.claim_test_verifier import verify_instance

            result = verify_instance(
                sample=sample,
                claim_tests_root=Path(claim_tests_root),
                use_container=cfg.get("use_container", True),
                timeout_s=cfg.get("timeout_s", 300),
                max_claims=cfg.get("max_claims"),
            )

            summary = result.get("summary", {})
            cvr = summary.get("cvr", 0.0)
            total = summary.get("total_claim_tests", 0)
            valid = summary.get("valid", 0)
            label_counts = summary.get("label_counts", {})

            cvr_threshold = cfg.get("cvr_threshold", 0.0)
            if result.get("error"):
                verdict = Verdict.ERROR.value
            elif total == 0:
                verdict = Verdict.SKIP.value
            elif cvr >= cvr_threshold:
                verdict = Verdict.ACCEPT.value
            else:
                verdict = Verdict.WARNING.value

            return LayerResult(
                layer="claim_test",
                verdict=verdict,
                score=cvr,
                details={
                    "total_claim_tests": total,
                    "valid": valid,
                    "cvr": cvr,
                    "label_counts": label_counts,
                    "instance_id": instance_id,
                },
                error=result.get("error"),
                duration_s=time.time() - t0,
            )

        except Exception as exc:
            logger.exception("Claim-test layer failed")
            return LayerResult(
                layer="claim_test",
                verdict=Verdict.ERROR.value,
                error=f"{type(exc).__name__}: {exc}",
                duration_s=time.time() - t0,
            )

    # ------------------------------------------------------------------
    # Verdict aggregation
    # ------------------------------------------------------------------

    def _aggregate(
        self, layers: Sequence[LayerResult]
    ) -> tuple:
        """
        Aggregate individual layer verdicts into a final verdict + reason.

        Returns (verdict_str, reason_str).
        """
        if not layers:
            return Verdict.ERROR.value, "No layers were executed"

        policy = self.cfg.get("aggregation", {}).get("policy", "all_pass")

        active = [lr for lr in layers if lr.verdict != Verdict.SKIP.value]
        if not active:
            return Verdict.SKIP.value, "All layers were skipped"

        rejects = [lr for lr in active if lr.verdict == Verdict.REJECT.value]
        errors = [lr for lr in active if lr.verdict == Verdict.ERROR.value]
        warnings = [lr for lr in active if lr.verdict == Verdict.WARNING.value]
        accepts = [lr for lr in active if lr.verdict == Verdict.ACCEPT.value]

        if policy == "all_pass":
            if rejects:
                names = ", ".join(lr.layer for lr in rejects)
                return Verdict.REJECT.value, f"Rejected by: {names}"
            if errors:
                names = ", ".join(lr.layer for lr in errors)
                return Verdict.ERROR.value, f"Errors in: {names}"
            if warnings:
                names = ", ".join(lr.layer for lr in warnings)
                return Verdict.WARNING.value, f"Warnings from: {names}"
            return Verdict.ACCEPT.value, "All layers passed"

        elif policy == "majority":
            if len(accepts) > len(active) / 2:
                return Verdict.ACCEPT.value, f"{len(accepts)}/{len(active)} layers passed"
            if rejects:
                return Verdict.REJECT.value, f"Majority did not pass ({len(accepts)}/{len(active)})"
            return Verdict.WARNING.value, f"{len(accepts)}/{len(active)} layers passed"

        elif policy == "any_pass":
            if accepts:
                return Verdict.ACCEPT.value, f"{len(accepts)}/{len(active)} layers passed"
            if rejects:
                return Verdict.REJECT.value, "No layer passed"
            return Verdict.WARNING.value, "No layer clearly passed"

        return Verdict.ERROR.value, f"Unknown aggregation policy: {policy}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the multi-layer verification harness against a patch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Static analysis only
  python -m verifier.multi_layer_harness \\
      --instance django__django-12345 --patch-file patch.diff \\
      --repo-path /tmp/django --layers static

  # All three layers
  python -m verifier.multi_layer_harness \\
      --instance astropy__astropy-7746 --patch-file patch.diff \\
      --repo-path /tmp/astropy --sample-file sample.json \\
      --claim-tests-root claim_test_generation/tests_out \\
      --layers static unit_test claim_test
        """,
    )
    parser.add_argument("--instance", required=True, help="Instance ID (e.g. django__django-12345)")
    parser.add_argument("--patch-file", required=True, help="Path to unified diff file")
    parser.add_argument("--repo-path", default=None, help="Path to checked-out repository with patch applied")
    parser.add_argument("--sample-file", default=None, help="Path to SWE-bench sample JSON (for claim-test layer)")
    parser.add_argument("--claim-tests-root", default=None, help="Root directory containing generated claim tests")
    parser.add_argument("--eval-script", default=None, help="Path to SWE-bench eval.sh script")
    parser.add_argument(
        "--layers",
        nargs="+",
        default=["static", "unit_test", "claim_test"],
        choices=["static", "unit_test", "claim_test"],
        help="Which layers to run (default: all three)",
    )
    parser.add_argument("--sqi-threshold", type=float, default=0.5, help="Minimum SQI score for static layer")
    parser.add_argument("--cvr-threshold", type=float, default=0.0, help="Minimum CVR for claim-test layer")
    parser.add_argument("--timeout", type=int, default=300, help="Per-layer timeout in seconds")
    parser.add_argument("--policy", default="all_pass", choices=["all_pass", "majority", "any_pass"], help="Verdict aggregation policy")
    parser.add_argument("--enable-rules", action="store_true", default=False, help="Enable supplementary verification rules in static layer")
    parser.add_argument("--output", default=None, help="Write JSON report to this file")
    parser.add_argument("--verbose", action="store_true", default=False)
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Read patch
    diff = Path(args.patch_file).read_text(encoding="utf-8")

    # Build patch_data
    patch_data: Dict[str, Any] = {
        "instance_id": args.instance,
        "diff": diff,
    }
    if args.repo_path:
        patch_data["repo_path"] = args.repo_path
    if args.eval_script:
        patch_data["eval_script"] = args.eval_script

    # Load SWE-bench sample if provided
    if args.sample_file:
        sample = json.loads(Path(args.sample_file).read_text(encoding="utf-8"))
        # If the file contains a list, pick the first element
        if isinstance(sample, list):
            sample = sample[0]
        patch_data["sample"] = sample

    if args.claim_tests_root:
        patch_data["claim_tests_root"] = args.claim_tests_root

    # Build config
    config = {
        "layers": args.layers,
        "static": {"sqi_threshold": args.sqi_threshold},
        "unit_test": {"timeout_s": args.timeout},
        "claim_test": {"timeout_s": args.timeout, "cvr_threshold": args.cvr_threshold},
        "rules": {"enabled": args.enable_rules},
        "aggregation": {"policy": args.policy},
    }

    harness = MultiLayerHarness(config=config)
    report = harness.run(patch_data)

    # Output
    report_json = report.to_json()
    print(report_json)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report_json, encoding="utf-8")
        print(f"\nReport written to {args.output}", file=__import__("sys").stderr)

    # Exit code: 0 for ACCEPT, 1 for REJECT/ERROR, 2 for WARNING/SKIP
    if report.verdict == Verdict.ACCEPT.value:
        raise SystemExit(0)
    elif report.verdict in (Verdict.REJECT.value, Verdict.ERROR.value):
        raise SystemExit(1)
    else:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
