"""
Unified Verification Pipeline
==============================
Orchestrates three verification layers behind a single ``run_pipeline()`` call:

  1. **Static**   — pylint, flake8, radon, mypy, bandit, AST validation
  2. **Dynamic**  — SWE-bench unit-test execution via Singularity
  3. **Semantic** — claim extraction (LLM) → agentic test-gen loop → BUG vs GOLD

Each layer is independently toggleable.  The Streamlit UI calls ``run_pipeline()``
with a ``PipelineConfig`` that specifies which layers to run and the vLLM endpoint
for the semantic layer.

Hypothesis fuzzing is excluded.
"""

from __future__ import annotations

import ast as _ast
import logging
import re
import shutil
import tempfile
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set

import sys

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------

class Layer(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    SEMANTIC = "semantic"


class LayerStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class LayerResult:
    layer: str
    status: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_s: float = 0.0


@dataclass
class VLLMConfig:
    endpoint: str = "http://127.0.0.1:8000/v1"
    model: str = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout_s: int = 120


@dataclass
class PipelineConfig:
    layers: Set[str] = field(default_factory=lambda: {Layer.STATIC, Layer.DYNAMIC, Layer.SEMANTIC})
    vllm: VLLMConfig = field(default_factory=VLLMConfig)
    repos_root: str = "repos_temp_pipeline"
    max_claims: int = 6
    max_attempts_per_claim: int = 4
    claim_test_timeout_s: int = 300


@dataclass
class AggregatedReport:
    instance_id: str
    repo: str
    timestamp: str = ""
    layers_requested: List[str] = field(default_factory=list)
    layers_completed: List[str] = field(default_factory=list)
    layers: Dict[str, LayerResult] = field(default_factory=dict)
    repo_path: Optional[str] = None
    container_path: Optional[str] = None
    overall_success: bool = False
    error: Optional[str] = None

    def summary(self) -> Dict[str, Any]:
        """Compact summary for dashboard display."""
        s: Dict[str, Any] = {
            "instance_id": self.instance_id,
            "repo": self.repo,
            "overall_success": self.overall_success,
            "layers_requested": self.layers_requested,
            "layers_completed": self.layers_completed,
        }
        for name, lr in self.layers.items():
            entry: Dict[str, Any] = {"status": lr.status}
            if name == Layer.STATIC and lr.data:
                cq = lr.data.get("code_quality", {})
                entry["sqi"] = cq.get("sqi", {}).get("SQI", 0)
            elif name == Layer.DYNAMIC and lr.data:
                entry["passed"] = lr.data.get("passed", 0)
                entry["failed"] = lr.data.get("failed", 0)
                entry["total"] = lr.data.get("total", 0)
            elif name == Layer.SEMANTIC and lr.data:
                sm = lr.data.get("summary", {})
                entry["total_claims"] = sm.get("total_claims", 0)
                entry["successful"] = sm.get("successful", 0)
                entry["cvr"] = sm.get("cvr", 0.0)
            s[name] = entry
        return s

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------

class ProgressCallback(Protocol):
    def on_phase(self, phase: str, detail: str = "") -> None: ...
    def on_layer_start(self, layer: str) -> None: ...
    def on_layer_end(self, layer: str, result: LayerResult) -> None: ...


class NullCallback:
    """No-op callback for headless / batch usage."""
    def on_phase(self, phase: str, detail: str = "") -> None:
        logger.info("%s %s", phase, detail)

    def on_layer_start(self, layer: str) -> None:
        logger.info("Starting layer: %s", layer)

    def on_layer_end(self, layer: str, result: LayerResult) -> None:
        logger.info("Layer %s → %s (%.1fs)", layer, result.status, result.duration_s)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_or_get_container(instance_id: str) -> Optional[Path]:
    from swebench_singularity import Config, SingularityBuilder
    config = Config()
    builder = SingularityBuilder(config)
    build_result = builder.build_instance(
        instance_id=instance_id,
        force_rebuild=False,
        check_docker_exists=False,
    )
    if build_result.success and build_result.sif_path:
        return build_result.sif_path
    logger.error("Container build failed for %s: %s", instance_id, build_result.error_message)
    return None


def _parse_test_counts(stdout: str) -> Dict[str, int]:
    counts: Dict[str, int] = {"passed": 0, "failed": 0, "errors": 0}
    for key in counts:
        m = re.search(rf"(\d+) {key}", stdout)
        if m:
            counts[key] = int(m.group(1))
    return counts


def _get_tests_from_sample(sample: Dict) -> tuple:
    """Extract FAIL_TO_PASS + PASS_TO_PASS and detect framework."""
    metadata = sample.get("metadata", {}) or {}
    f2p_raw = metadata.get("FAIL_TO_PASS", "[]")
    p2p_raw = metadata.get("PASS_TO_PASS", "[]")

    try:
        f2p = _ast.literal_eval(f2p_raw) if isinstance(f2p_raw, str) else f2p_raw
    except Exception:
        f2p = []
    try:
        p2p = _ast.literal_eval(p2p_raw) if isinstance(p2p_raw, str) else p2p_raw
    except Exception:
        p2p = []

    all_tests = [t for t in (f2p + p2p) if isinstance(t, str) and t.strip()]

    django_like = sum(1 for t in all_tests if "(" in t and ")" in t and "::" not in t)
    pytest_like = sum(1 for t in all_tests if "::" in t or t.endswith(".py"))
    prefer_django = django_like > 0 and django_like >= pytest_like
    framework_hint = "django" if prefer_django else None

    return all_tests, framework_hint


# ---------------------------------------------------------------------------
# Layer 1: Static
# ---------------------------------------------------------------------------

def _run_static_layer(
    repo_path: Path,
    patch_str: str,
    callback: ProgressCallback,
) -> LayerResult:
    t0 = time.time()
    data: Dict[str, Any] = {}
    try:
        from verifier.static_analyzers.code_quality import analyze as run_code_quality
        from verifier.static_analyzers.syntax_structure import run_syntax_structure_analysis

        callback.on_phase("Static", "Running code quality analysis (pylint, flake8, radon, mypy, bandit)...")
        data["code_quality"] = run_code_quality(str(repo_path), patch_str)

        callback.on_phase("Static", "Running syntax & structure analysis (AST validation)...")
        data["syntax_structure"] = run_syntax_structure_analysis(str(repo_path), patch_str)

        return LayerResult(
            layer=Layer.STATIC,
            status=LayerStatus.SUCCESS,
            data=data,
            duration_s=time.time() - t0,
        )
    except Exception as exc:
        logger.exception("Static layer failed")
        return LayerResult(
            layer=Layer.STATIC,
            status=LayerStatus.FAILED,
            data=data,
            error=f"{type(exc).__name__}: {exc}",
            duration_s=time.time() - t0,
        )


# ---------------------------------------------------------------------------
# Layer 2: Dynamic
# ---------------------------------------------------------------------------

def _run_dynamic_layer(
    repo_path: Path,
    sample: Dict,
    container_path: Path,
    callback: ProgressCallback,
) -> LayerResult:
    t0 = time.time()
    data: Dict[str, Any] = {}
    try:
        from verifier.dynamic_analyzers import test_patch_singularity

        callback.on_phase("Dynamic", "Installing package dependencies in container...")
        test_patch_singularity.install_package_in_singularity(
            repo_path=repo_path,
            image_path=str(container_path),
        )

        tests, framework_hint = _get_tests_from_sample(sample)
        callback.on_phase("Dynamic", f"Running {len(tests)} unit tests in Singularity...")

        test_run = test_patch_singularity.run_tests_in_singularity(
            repo_path=repo_path,
            tests=tests,
            image_path=str(container_path),
            collect_coverage=False,
            test_framework_hint=framework_hint,
            verbose=True,
        )

        stdout = test_run.get("stdout", "")
        stderr = test_run.get("stderr", "")
        returncode = test_run.get("returncode", -1)
        counts = _parse_test_counts(stdout)

        data = {
            "success": returncode == 0,
            "passed": counts["passed"],
            "failed": counts["failed"],
            "errors": counts["errors"],
            "total": sum(counts.values()),
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
            "execution_mode": "singularity",
            "tests_run": len(tests),
            "container": str(container_path),
        }

        return LayerResult(
            layer=Layer.DYNAMIC,
            status=LayerStatus.SUCCESS,
            data=data,
            duration_s=time.time() - t0,
        )
    except Exception as exc:
        logger.exception("Dynamic layer failed")
        return LayerResult(
            layer=Layer.DYNAMIC,
            status=LayerStatus.FAILED,
            data=data,
            error=f"{type(exc).__name__}: {exc}",
            duration_s=time.time() - t0,
        )


# ---------------------------------------------------------------------------
# Layer 3: Semantic (claim extraction + agentic loop)
# ---------------------------------------------------------------------------

def _run_semantic_layer(
    sample: Dict,
    repo_path: Path,
    container_path: Optional[Path],
    vllm_config: VLLMConfig,
    config: PipelineConfig,
    callback: ProgressCallback,
) -> LayerResult:
    t0 = time.time()
    data: Dict[str, Any] = {}

    try:
        # ---- Sub-phase 1: Claim Extraction ----
        callback.on_phase("Semantic", "Extracting behavioral claims via LLM...")

        from claim_extraction.llm.factory import build_llm_client
        from claim_extraction.pipeline.runner import build_prompt_env, process_instance
        from claim_extraction.prepare_instances import load_touched_file_texts

        cfg = {
            "llm": {
                "backend": "vllm",
                "endpoint": vllm_config.endpoint,
                "model": vllm_config.model,
                "api_key": vllm_config.api_key,
                "temperature": vllm_config.temperature,
                "max_tokens": vllm_config.max_tokens,
                "timeout_s": vllm_config.timeout_s,
            },
            "extraction": {
                "min_claim_score": 2,
                "check_eligibility": True,
                "require_grounding": True,
                "max_claims_per_issue": config.max_claims,
            },
            "context": {"max_chars": 22000},
            "parsing": {"allow_repair": True},
            "eligibility": {"threshold": 2},
            "schema_version": "2.2",
        }

        llm_client = build_llm_client(cfg["llm"])
        prompt_env = build_prompt_env()

        # Build touched_files_text from the cloned repo for grounding
        patch_str_for_grounding = sample.get("patch", "")
        touched_files_text = load_touched_file_texts(repo_path, patch_str_for_grounding)
        callback.on_phase("Semantic", f"Loaded {len(touched_files_text)} touched file(s) for grounding")

        claim_result = process_instance(
            sample,
            cfg=cfg,
            llm=llm_client,
            prompt_env=prompt_env,
            template_name="claim_prompt_v2_1.jinja",
            touched_files_text=touched_files_text,
        )

        extraction_dict = claim_result.to_dict()
        data["extraction"] = extraction_dict

        claims = extraction_dict.get("claims", [])
        eligible = extraction_dict.get("eligible", False)
        stats = extraction_dict.get("stats", {})

        callback.on_phase(
            "Semantic",
            f"Extracted {len(claims)} grounded claims "
            f"(eligible={eligible}, avg_score={stats.get('avg_score', 0):.1f})",
        )

        ungrounded = extraction_dict.get("ungrounded_claims", [])
        low_score = extraction_dict.get("low_score_claims", [])
        total_raw = len(claims) + len(ungrounded) + len(low_score)

        if not claims:
            reason = "No grounded claims extracted"
            if ungrounded:
                reason += f" ({len(ungrounded)} ungrounded)"
            if low_score:
                reason += f" ({len(low_score)} low-score)"
            callback.on_phase("Semantic", f"{reason}. Skipping agentic loop.")
            data["claim_loop_results"] = []
            data["summary"] = {
                "total_claims": 0,
                "successful": 0,
                "failed": 0,
                "cvr": 0.0,
                "total_extracted_raw": total_raw,
                "ungrounded": len(ungrounded),
                "low_score": len(low_score),
                "label_distribution": {},
                "note": reason,
            }
            return LayerResult(
                layer=Layer.SEMANTIC,
                status=LayerStatus.FAILED,
                data=data,
                error=reason,
                duration_s=time.time() - t0,
            )

        # ---- Sub-phase 2: Agentic Loop per claim ----
        callback.on_phase("Semantic", "Starting agentic test-generation loop...")

        from agentic_closed_loop.loop import AgenticClosedLoop, LoopConfig
        from claim_test_generation.claim_test_generator import VLLMClient as TestGenVLLMClient

        testgen_client = TestGenVLLMClient(
            endpoint=vllm_config.endpoint,
            model=vllm_config.model,
            temperature=vllm_config.temperature,
            max_tokens=vllm_config.max_tokens,
            timeout_s=vllm_config.timeout_s,
            api_key=vllm_config.api_key,
        )

        # Temp directory for generated tests
        tests_tmp = Path(tempfile.mkdtemp(prefix="unified_tests_"))

        loop_config = LoopConfig(
            tests_root=tests_tmp / "tests_out",
            claim_tests_root=tests_tmp / "tests_out",
            repos_root=Path(config.repos_root),
            max_attempts=config.max_attempts_per_claim,
            timeout_s=config.claim_test_timeout_s,
        )

        limited_claims = claims[: config.max_claims]
        results_per_claim: List[Dict[str, Any]] = []

        for i, claim in enumerate(limited_claims, 1):
            claim_id = claim.get("claim_id", f"C{i}")
            callback.on_phase(
                "Semantic",
                f"Agentic loop for claim {claim_id} ({i}/{len(limited_claims)})...",
            )

            try:
                loop = AgenticClosedLoop(
                    sample=sample,
                    claim=claim,
                    client=testgen_client,
                    config=loop_config,
                    issue_context=extraction_dict.get("issue_context"),
                )
                payload = loop.run()
                results_per_claim.append(payload)

                status_str = "SUCCESS" if payload.get("success") else payload.get("failure_reason", "failed")
                attempts_count = len(payload.get("attempts", []))
                callback.on_phase(
                    "Semantic",
                    f"  Claim {claim_id}: {status_str} ({attempts_count} attempt(s))",
                )
            except Exception as exc:
                logger.warning("Agentic loop failed for claim %s: %s", claim_id, exc)
                results_per_claim.append({
                    "instance_id": sample.get("instance_id", ""),
                    "claim_id": claim_id,
                    "success": False,
                    "failure_reason": f"exception: {exc}",
                    "attempts": [],
                })

        # Cleanup temp dir
        shutil.rmtree(tests_tmp, ignore_errors=True)

        # Summarize with label distribution
        total = len(results_per_claim)
        successful = sum(1 for r in results_per_claim if r.get("success"))
        cvr = successful / total if total > 0 else 0.0

        # Count verification labels from final attempts
        from collections import Counter
        label_counts: Counter = Counter()
        for r in results_per_claim:
            attempts = r.get("attempts", [])
            if not attempts:
                label_counts["NO_ATTEMPTS"] += 1
                continue
            last = attempts[-1]
            if isinstance(last, dict):
                # Check verification_result first
                vr = last.get("verification_result", {})
                if isinstance(vr, dict):
                    for t in vr.get("tests", []):
                        lbl = t.get("classification", {}).get("label", "UNKNOWN")
                        label_counts[lbl] += 1
                        break
                    else:
                        # Fallback to failure_classification
                        fc = last.get("failure_classification", {})
                        label_counts[fc.get("label", "UNKNOWN").upper()] += 1
                else:
                    label_counts["UNKNOWN"] += 1
            else:
                label_counts["UNKNOWN"] += 1

        data["claim_loop_results"] = results_per_claim
        data["summary"] = {
            "total_claims": total,
            "successful": successful,
            "failed": total - successful,
            "cvr": cvr,
            "total_extracted_raw": total_raw,
            "grounded": len(claims),
            "ungrounded": len(ungrounded),
            "low_score": len(low_score),
            "label_distribution": dict(label_counts),
        }

        callback.on_phase(
            "Semantic",
            f"Semantic complete: {successful}/{total} claims validated (CVR={cvr:.0%})",
        )

        return LayerResult(
            layer=Layer.SEMANTIC,
            status=LayerStatus.SUCCESS,
            data=data,
            duration_s=time.time() - t0,
        )

    except Exception as exc:
        logger.exception("Semantic layer failed")
        return LayerResult(
            layer=Layer.SEMANTIC,
            status=LayerStatus.FAILED,
            data=data,
            error=f"{type(exc).__name__}: {exc}",
            duration_s=time.time() - t0,
        )


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    sample: Dict[str, Any],
    config: PipelineConfig,
    callback: Optional[ProgressCallback] = None,
) -> AggregatedReport:
    """
    Run the unified verification pipeline on a single SWE-bench sample.

    Parameters
    ----------
    sample : dict
        Normalized SWE-bench sample from DatasetLoader.
    config : PipelineConfig
        Which layers to run and configuration for each.
    callback : ProgressCallback, optional
        Hook for real-time status updates (e.g. Streamlit).

    Returns
    -------
    AggregatedReport
    """
    if callback is None:
        callback = NullCallback()

    metadata = sample.get("metadata", {}) or {}
    instance_id = metadata.get("instance_id") or sample.get("instance_id", "unknown")
    repo_name = sample.get("repo", "unknown")
    layers = config.layers

    report = AggregatedReport(
        instance_id=instance_id,
        repo=repo_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        layers_requested=sorted(layers),
    )

    # ---- Phase 0: Clone & Patch ----
    callback.on_phase("Setup", "Cloning repository...")
    try:
        from swebench_integration import PatchLoader

        patcher = PatchLoader(sample=sample, repos_root=config.repos_root)
        repo_path = Path(patcher.clone_repository())
        report.repo_path = str(repo_path)
        callback.on_phase("Setup", f"Repository cloned to {repo_path}")
    except Exception as exc:
        report.error = f"Clone failed: {exc}"
        callback.on_phase("Setup", f"ERROR: {report.error}")
        return report

    callback.on_phase("Setup", "Applying patch...")
    try:
        patch_result = patcher.apply_patch()
        if not patch_result.get("applied"):
            report.error = "Patch application failed"
            callback.on_phase("Setup", f"ERROR: {report.error}")
            return report
        callback.on_phase("Setup", "Patch applied successfully")
    except Exception as exc:
        report.error = f"Patch apply failed: {exc}"
        callback.on_phase("Setup", f"ERROR: {report.error}")
        return report

    # Apply test patch if present
    test_patch = metadata.get("test_patch", "")
    if test_patch and str(test_patch).strip():
        try:
            patcher.apply_additional_patch(str(test_patch))
            callback.on_phase("Setup", "Test patch applied")
        except Exception as exc:
            callback.on_phase("Setup", f"Warning: test patch failed: {exc}")

    patch_str = sample.get("patch", "")

    # ---- Container (needed by dynamic + semantic) ----
    container_path: Optional[Path] = None
    need_container = bool(set(layers) & {Layer.DYNAMIC, Layer.SEMANTIC})
    if need_container:
        callback.on_phase("Setup", "Preparing Singularity container...")
        container_path = _build_or_get_container(instance_id)
        if container_path:
            report.container_path = str(container_path)
            callback.on_phase("Setup", f"Container ready: {container_path.name}")
        else:
            callback.on_phase("Setup", "WARNING: Container build failed")

    # ---- Layer 1: Static ----
    if Layer.STATIC in layers:
        callback.on_layer_start(Layer.STATIC)
        result = _run_static_layer(repo_path, patch_str, callback)
        report.layers[Layer.STATIC] = result
        callback.on_layer_end(Layer.STATIC, result)
        if result.status == LayerStatus.SUCCESS:
            report.layers_completed.append(Layer.STATIC)

    # ---- Layer 2: Dynamic ----
    if Layer.DYNAMIC in layers:
        callback.on_layer_start(Layer.DYNAMIC)
        if container_path:
            result = _run_dynamic_layer(repo_path, sample, container_path, callback)
        else:
            result = LayerResult(
                layer=Layer.DYNAMIC,
                status=LayerStatus.FAILED,
                error="No Singularity container available",
            )
        report.layers[Layer.DYNAMIC] = result
        callback.on_layer_end(Layer.DYNAMIC, result)
        if result.status == LayerStatus.SUCCESS:
            report.layers_completed.append(Layer.DYNAMIC)

    # ---- Layer 3: Semantic ----
    if Layer.SEMANTIC in layers:
        callback.on_layer_start(Layer.SEMANTIC)
        result = _run_semantic_layer(
            sample=sample,
            repo_path=repo_path,
            container_path=container_path,
            vllm_config=config.vllm,
            config=config,
            callback=callback,
        )
        report.layers[Layer.SEMANTIC] = result
        callback.on_layer_end(Layer.SEMANTIC, result)
        if result.status == LayerStatus.SUCCESS:
            report.layers_completed.append(Layer.SEMANTIC)

    # ---- Overall verdict ----
    report.overall_success = set(report.layers_completed) == set(report.layers_requested)
    return report


# ---------------------------------------------------------------------------
# Candidate Patch Validation (post-hoc verification)
# ---------------------------------------------------------------------------

def run_candidate_validation(
    instance_id: str,
    claim_id: str = "C1",
    tests_model: str = "Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
    include_failed: bool = True,
    max_candidates: Optional[int] = None,
    timeout_s: int = 300,
    callback: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    """
    Run candidate patch verification for a single instance/claim.

    Uses pre-computed VALID discriminative tests from the agentic closed loop
    and runs them against candidate patches from SWE-bench experiments.

    Parameters
    ----------
    instance_id : str
        SWE-bench instance ID.
    claim_id : str
        Claim identifier (e.g. "C1").
    tests_model : str
        Which model's generated tests to use.
    include_failed : bool
        Also test patches that failed SWE-bench evaluation.
    max_candidates : int, optional
        Limit number of candidate patches to test.
    timeout_s : int
        Per-test timeout in seconds.
    callback : ProgressCallback, optional
        Hook for real-time status updates.

    Returns
    -------
    dict with verification results and summary.
    """
    if callback is None:
        callback = NullCallback()

    from claim_test_verification.candidate_verifier import (
        run_candidate_verification,
    )

    def progress_fn(msg: str):
        callback.on_phase("Candidate Validation", msg)

    return run_candidate_verification(
        instance_id=instance_id,
        claim_id=claim_id,
        tests_model=tests_model,
        include_failed=include_failed,
        max_candidates=max_candidates,
        timeout_s=timeout_s,
        progress_callback=progress_fn,
    )
