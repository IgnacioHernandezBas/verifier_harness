"""
SWE-bench Unified Verification App

A Streamlit application for:
- Testing patches on SWE-bench instances OR custom codebases
- Running three verification layers: Static, Dynamic, Semantic
- Displaying comprehensive aggregated verification results
"""

import streamlit as st
import json
import tempfile
import shutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from swebench_integration import DatasetLoader, PatchLoader
from verifier.static_analyzers.code_quality import analyze as run_static_analysis
from swebench_singularity import Config, SingularityBuilder, InstanceRunner
from verifier.dynamic_analyzers import test_patch_singularity
from unified_pipeline import (
    Layer, LayerStatus, LayerResult, VLLMConfig, PipelineConfig,
    AggregatedReport, ProgressCallback, run_pipeline,
)

# Set page config
st.set_page_config(
    page_title="E6 Verifier Harness",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []
if 'vllm_connected' not in st.session_state:
    st.session_state.vllm_connected = False


# ---------------------------------------------------------------------------
# Streamlit progress callback
# ---------------------------------------------------------------------------

class StreamlitCallback:
    """Real-time progress feedback via st.status()."""

    def __init__(self):
        self._container = st.status("Initializing pipeline...", expanded=True)

    def on_phase(self, phase: str, detail: str = "") -> None:
        msg = f"{phase}: {detail}" if detail else phase
        self._container.update(label=msg)
        self._container.write(msg)

    def on_layer_start(self, layer: str) -> None:
        label = {
            Layer.STATIC: "Running Static Analysis...",
            Layer.DYNAMIC: "Running Dynamic Analysis...",
            Layer.SEMANTIC: "Running Semantic Analysis...",
        }.get(layer, f"Running {layer}...")
        self._container.update(label=label)
        self._container.write(f"--- Starting {layer} layer ---")

    def on_layer_end(self, layer: str, result: LayerResult) -> None:
        icon = "+" if result.status == LayerStatus.SUCCESS else "x"
        self._container.write(
            f"[{icon}] {layer}: {result.status} ({result.duration_s:.1f}s)"
        )

    def done(self, success: bool = True):
        if success:
            self._container.update(label="Pipeline complete", state="complete")
        else:
            self._container.update(label="Pipeline finished with errors", state="error")


# ---------------------------------------------------------------------------
# vLLM connection helper
# ---------------------------------------------------------------------------

def test_vllm_connection(endpoint: str) -> tuple[bool, str]:
    """Test connectivity to vLLM server. Returns (ok, message)."""
    try:
        # Strip /v1 suffix for models endpoint
        base = endpoint.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        url = f"{base}/models"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("id", "?") for m in data.get("data", [])]
            return True, f"Connected. Models: {', '.join(models)}"
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.ConnectionError:
        return False, f"Cannot connect to {endpoint}. Is vLLM running?"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Container helpers (kept from original)
# ---------------------------------------------------------------------------

def get_or_build_container(instance_id: Optional[str] = None,
                           docker_image: Optional[str] = None,
                           container_file: Optional[str] = None) -> Optional[Path]:
    """Get or build a Singularity container."""
    try:
        config = Config()
        builder = SingularityBuilder(config)

        if instance_id:
            st.write(f"Building container for {instance_id}...")
            result = builder.build_instance(
                instance_id=instance_id,
                force_rebuild=False,
                check_docker_exists=False
            )
            if result.success:
                from_cache = " (cached)" if result.from_cache else " (newly built)"
                st.success(f"Container ready{from_cache}")
                return result.sif_path
            else:
                st.error(f"Container build failed: {result.error_message}")
                return None

        elif docker_image:
            st.write(f"Converting Docker image: {docker_image}...")
            import hashlib
            pseudo_id = hashlib.md5(docker_image.encode()).hexdigest()[:12]
            result = builder.build_from_docker(
                docker_image=docker_image,
                output_name=f"custom_{pseudo_id}.sif"
            )
            if result.success:
                st.success("Container built from Docker image")
                return result.sif_path
            else:
                st.error(f"Build failed: {result.error_message}")
                return None

        elif container_file:
            st.success("Using uploaded container")
            return Path(container_file)

        return None

    except Exception as e:
        st.error(f"Container setup failed: {e}")
        return None


def list_cached_containers() -> List[Dict]:
    """List all cached Singularity containers."""
    try:
        possible_paths = [
            Path("/fs/nexus-scratch/ihbas/.cache/swebench_singularity"),
            Path("/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache"),
            Path.home() / ".cache" / "swebench_singularity",
        ]

        try:
            config = Config()
            config_path = Path(config.get("singularity.cache_dir"))
            if config_path not in possible_paths:
                possible_paths.insert(0, config_path)
        except Exception:
            pass

        cache_dir = None
        for path in possible_paths:
            if path.exists():
                sif_files = list(path.rglob("*.sif"))
                if sif_files:
                    cache_dir = path
                    break

        if not cache_dir:
            return []

        containers = []
        for sif_file in cache_dir.rglob("*.sif"):
            try:
                stat = sif_file.stat()
                containers.append({
                    'name': sif_file.name,
                    'path': str(sif_file),
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception:
                continue

        return sorted(containers, key=lambda x: x['modified'], reverse=True)

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_aggregated_dashboard(report: AggregatedReport):
    """3-column dashboard showing status of each layer."""
    st.subheader("Aggregated Dashboard")

    cols = st.columns(3)
    layer_info = [
        (Layer.STATIC, "Static Analysis", "SQI"),
        (Layer.DYNAMIC, "Dynamic Analysis", "Tests"),
        (Layer.SEMANTIC, "Semantic Analysis", "CVR"),
    ]

    for col, (layer_key, label, metric_label) in zip(cols, layer_info):
        with col:
            lr = report.layers.get(layer_key)
            if lr is None:
                st.metric(label, "Not requested")
                continue

            status = lr.status
            if status == LayerStatus.SUCCESS:
                status_icon = "[OK]"
            elif status == LayerStatus.FAILED:
                status_icon = "[FAIL]"
            elif status == LayerStatus.SKIPPED:
                status_icon = "[SKIP]"
            else:
                status_icon = f"[{status}]"

            # Extract key metric
            if layer_key == Layer.STATIC and lr.data:
                cq = lr.data.get("code_quality", {})
                sqi = cq.get("sqi", {}).get("SQI", 0)
                st.metric(label, f"{sqi:.1f}", status_icon)
            elif layer_key == Layer.DYNAMIC and lr.data:
                passed = lr.data.get("passed", 0)
                total = lr.data.get("total", 0)
                st.metric(label, f"{passed}/{total} passed", status_icon)
            elif layer_key == Layer.SEMANTIC and lr.data:
                sm = lr.data.get("summary", {})
                total_c = sm.get("total_claims", 0)
                if total_c > 0:
                    cvr = sm.get("cvr", 0)
                    succ_c = sm.get("successful", 0)
                    st.metric(label, f"CVR {cvr:.0%} ({succ_c}/{total_c})", status_icon)
                else:
                    ext = lr.data.get("extraction", {})
                    raw = len(ext.get("claims", [])) + len(ext.get("ungrounded_claims", [])) + len(ext.get("low_score_claims", []))
                    grounded = len(ext.get("claims", []))
                    st.metric(label, f"0 testable ({grounded}/{raw} grounded)", status_icon)
            else:
                st.metric(label, status_icon)

            if lr.error:
                st.caption(f"Error: {lr.error[:100]}")
            st.caption(f"Duration: {lr.duration_s:.1f}s")


def display_static_analysis(static_results: Dict):
    """Display static analysis results."""
    st.subheader("Static Analysis Results")

    if 'error' in static_results:
        st.error(f"Static analysis error: {static_results['error']}")
        return

    # SQI Score
    sqi = static_results.get('sqi', {})
    sqi_score = sqi.get('SQI', 0)
    classification = sqi.get('classification', 'Unknown')

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.metric("Static Quality Index (SQI)", f"{sqi_score:.1f}/100", classification)

    with col2:
        modified_files = static_results.get('modified_files', [])
        st.metric("Modified Files", len(modified_files))

    with col3:
        total_issues = 0
        if 'flake8' in static_results:
            total_issues += len(static_results['flake8'])
        if 'mypy' in static_results:
            total_issues += static_results['mypy'].get('error_count', 0)
        st.metric("Total Issues", total_issues)

    # Component breakdown
    st.write("**Component Breakdown:**")
    components = sqi.get('components', {})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Pylint", f"{components.get('pylint', 0):.1f}")
    with col2:
        st.metric("Radon", f"{components.get('radon', 0):.1f}")
    with col3:
        st.metric("Flake8", f"{components.get('flake8', 0):.1f}")
    with col4:
        st.metric("Mypy", f"{components.get('mypy', 0):.1f}")
    with col5:
        st.metric("Bandit", f"{components.get('bandit', 0):.1f}")

    st.divider()

    # Pylint
    if 'pylint' in static_results:
        pylint_issues = static_results['pylint']
        total_pylint = sum(len(issues) for issues in pylint_issues.values())
        with st.expander(f"Pylint Issues ({total_pylint})"):
            for file_path, issues in pylint_issues.items():
                if issues:
                    st.markdown(f"**{file_path}**")
                    for issue in issues[:5]:
                        st.write(f"- Line {issue.get('line')}: [{issue.get('type')}] {issue.get('message')}")

    # Flake8
    if 'flake8' in static_results:
        flake8_issues = static_results['flake8']
        with st.expander(f"Flake8 Issues ({len(flake8_issues)})"):
            for issue in flake8_issues[:10]:
                st.write(f"- Line {issue.get('line')}: [{issue.get('code')}] {issue.get('message')}")

    # Radon
    if 'radon' in static_results:
        radon = static_results['radon']
        with st.expander(f"Radon Complexity (MI: {radon.get('mi_avg', 0):.1f})"):
            complexity = radon.get('complexity', {})
            for file_path, functions in complexity.items():
                if functions:
                    st.markdown(f"**{file_path}**")
                    for func in functions:
                        st.write(f"- {func.get('name')}: Complexity {func.get('complexity')}")

    # Mypy
    if 'mypy' in static_results:
        mypy = static_results['mypy']
        error_count = mypy.get('error_count', 0)
        with st.expander(f"Mypy Type Errors ({error_count})"):
            errors = mypy.get('errors', [])
            for error in errors[:10]:
                st.write(f"- Line {error.get('line')}: {error.get('message')}")

    # Bandit
    if 'bandit' in static_results:
        bandit = static_results['bandit']
        total_bandit = sum(bandit.values())
        with st.expander(f"Bandit Security Issues ({total_bandit})"):
            st.write(f"- High: {bandit.get('HIGH', 0)}")
            st.write(f"- Medium: {bandit.get('MEDIUM', 0)}")
            st.write(f"- Low: {bandit.get('LOW', 0)}")


def display_syntax_structure(syntax_data: list):
    """Display syntax/structure analysis results."""
    st.subheader("Syntax & Structure Analysis")

    if not syntax_data:
        st.info("No syntax/structure results available")
        return

    # Summary row
    valid_count = sum(1 for e in syntax_data if e.get("is_code_valid", False))
    st.write(f"**Files analyzed:** {len(syntax_data)} | **Valid AST:** {valid_count}/{len(syntax_data)}")

    for entry in syntax_data:
        file_path = entry.get("path", entry.get("file", "unknown"))
        is_valid = entry.get("is_code_valid", False)
        status = "[OK]" if is_valid else "[INVALID]"
        with st.expander(f"{status} {file_path}"):
            if "error" in entry:
                st.error(entry["error"])
                continue

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Functions", entry.get("n_functions", 0))
            with c2:
                st.metric("Classes", entry.get("n_classes", 0))
            with c3:
                st.metric("Lines", entry.get("n_lines", 0))
            with c4:
                ratio = entry.get("ast_diff_ratio", 0)
                st.metric("AST Diff Ratio", f"{ratio:.2f}" if ratio else "N/A")

            # Changed functions
            changed = entry.get("changed_functions", [])
            if changed:
                st.write(f"**Changed functions ({len(changed)}):**")
                for func in changed:
                    if isinstance(func, dict):
                        st.write(f"- `{func.get('name', '?')}` (line {func.get('lineno', '?')})")
                    else:
                        st.write(f"- `{func}`")

            # Syntax errors
            syntax_errors = entry.get("syntax_errors", [])
            if syntax_errors:
                st.warning("Syntax errors found:")
                for err in syntax_errors:
                    st.write(f"- {err}")


def display_test_results(test_results: Dict):
    """Display test results."""
    st.subheader("Test Results")

    if 'error' in test_results:
        st.error(f"Test execution error: {test_results['error']}")
        return

    exec_mode = test_results.get('execution_mode', 'host')
    if exec_mode == 'singularity':
        container_name = Path(test_results.get('container', '')).name
        st.info(f"Tests executed in Singularity container: `{container_name}`")
    else:
        st.info("Tests executed on host system")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = test_results.get('total', 0)
        st.metric("Total Tests", total)
    with col2:
        passed = test_results.get('passed', 0)
        st.metric("Passed", passed)
    with col3:
        failed = test_results.get('failed', 0)
        st.metric("Failed", failed)
    with col4:
        errors = test_results.get('errors', 0)
        st.metric("Errors", errors)

    if total > 0:
        pass_rate = (passed / total) * 100
        st.progress(pass_rate / 100)
        st.write(f"**Pass Rate:** {pass_rate:.1f}%")
    elif test_results.get('tests_run', 0) > 0:
        st.warning(f"{test_results['tests_run']} tests attempted but no results parsed from output")

    stdout = test_results.get('stdout', '')
    with st.expander("Test Output (stdout)" + (" - Click to view" if stdout else " - Empty")):
        if stdout:
            st.code(stdout[-10000:] if len(stdout) > 10000 else stdout, language='text')
        else:
            st.write("No stdout captured")

    if test_results.get('stderr'):
        with st.expander("Test Errors (stderr)"):
            stderr = test_results.get('stderr', '')
            st.code(stderr[-5000:] if len(stderr) > 5000 else stderr, language='text')


def display_semantic_results(semantic_data: Dict):
    """Display semantic analysis results: claim extraction + agentic loop."""
    st.subheader("Semantic Analysis Results")

    if not semantic_data:
        st.info("No semantic results available")
        return

    # --- Sub-section 1: Claim Extraction ---
    extraction = semantic_data.get("extraction", {})
    if extraction:
        st.markdown("#### Claim Extraction")

        claims = extraction.get("claims", [])
        ungrounded = extraction.get("ungrounded_claims", [])
        low_score = extraction.get("low_score_claims", [])
        stats = extraction.get("stats", {})

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            total_raw = len(claims) + len(ungrounded) + len(low_score)
            st.metric("Total Extracted", total_raw)
        with c2:
            st.metric("Grounded Claims", len(claims))
        with c3:
            st.metric("Ungrounded", len(ungrounded))
        with c4:
            st.metric("Low Score", len(low_score))
        with c5:
            avg_score = stats.get("avg_score", 0)
            st.metric("Avg Score", f"{avg_score:.1f}" if avg_score else "N/A")

        # Show each grounded claim
        if claims:
            with st.expander(f"Grounded Claims ({len(claims)}) - click to view"):
                for i, claim in enumerate(claims, 1):
                    claim_id = claim.get("claim_id", f"C{i}")
                    score = claim.get("score", "?")
                    text = claim.get("text", claim.get("claim", "No text"))
                    targets = claim.get("target_symbols", [])

                    st.markdown(f"**{claim_id}** | Score: {score}")
                    st.write(text)
                    if targets:
                        st.caption(f"Target symbols: {', '.join(targets)}")

                    # Show grounding details if available
                    grounding = claim.get("grounding", {})
                    if grounding:
                        matched = grounding.get("matched_symbols", [])
                        if matched:
                            st.caption(f"Grounded on: {', '.join(matched[:5])}")
                    st.markdown("---")

        if ungrounded:
            with st.expander(f"Ungrounded Claims ({len(ungrounded)})"):
                for claim in ungrounded:
                    st.write(f"- {claim.get('text', claim.get('claim', '?'))}")

    # --- Sub-section 2: Agentic Loop Results ---
    loop_results = semantic_data.get("claim_loop_results", [])
    if loop_results:
        st.markdown("#### Agentic Loop Results (per claim)")

        # Summary table
        table_data = []
        for r in loop_results:
            attempts = r.get("attempts", [])
            # Get the final verification label from the last attempt
            final_label = "-"
            if attempts:
                last = attempts[-1]
                if isinstance(last, dict):
                    vr = last.get("verification_result", {})
                    if isinstance(vr, dict):
                        tests = vr.get("tests", [])
                        if tests:
                            final_label = tests[0].get("classification", {}).get("label", "-")
                    fc = last.get("failure_classification", {})
                    if isinstance(fc, dict) and final_label == "-":
                        final_label = fc.get("label", "-")

            table_data.append({
                "Claim": r.get("claim_id", "?"),
                "Attempts": len(attempts),
                "Status": "PASS" if r.get("success") else "FAIL",
                "Verification Label": final_label,
                "Failure Reason": r.get("failure_reason", "-") if not r.get("success") else "-",
            })

        st.table(table_data)

        # Expandable per-claim details
        for r in loop_results:
            claim_id = r.get("claim_id", "?")
            success = r.get("success", False)
            status_text = "PASS" if success else "FAIL"
            attempts = r.get("attempts", [])

            with st.expander(f"Claim {claim_id} [{status_text}] - {len(attempts)} attempt(s)"):
                for j, attempt in enumerate(attempts, 1):
                    if not isinstance(attempt, dict):
                        st.write(f"Attempt {j}: {attempt}")
                        continue

                    st.markdown(f"**Attempt {j}**")

                    # Status
                    att_status = attempt.get("status", "")
                    if att_status == "guardrail_failed":
                        fc = attempt.get("failure_classification", {})
                        st.warning(f"Guardrail failed: {fc.get('label', '?')} - {fc.get('details', '')}")
                        st.markdown("---")
                        continue

                    # Plan summary
                    plan = attempt.get("plan", {})
                    if plan:
                        strategy = plan.get("strategy", plan.get("summary", ""))
                        if strategy:
                            st.write(f"**Plan:** {strategy}")

                    # Guardrail result
                    guard = attempt.get("guardrail", {})
                    if guard:
                        st.write(f"**Guardrails:** {'PASS' if guard.get('ok') else 'FAIL'}")

                    # Test sketch
                    sketch = attempt.get("test_sketch", {})
                    if sketch:
                        desc = sketch.get("description", sketch.get("summary", ""))
                        if desc:
                            st.write(f"**Test sketch:** {desc}")

                    # Generated code
                    code = attempt.get("generated_code", "")
                    if code:
                        with st.expander(f"Generated test code (attempt {j})", expanded=(j == len(attempts))):
                            st.code(code, language="python")

                    # Verification result (BUG vs GOLD)
                    vr = attempt.get("verification_result", {})
                    if isinstance(vr, dict) and vr.get("tests"):
                        st.markdown("**BUG vs GOLD Verification:**")
                        for test_entry in vr.get("tests", []):
                            bug_run = test_entry.get("bug", {})
                            gold_run = test_entry.get("gold", {})
                            classification = test_entry.get("classification", {})
                            label = classification.get("label", "?")
                            reason = classification.get("reason", "")

                            b1, b2, b3 = st.columns(3)
                            with b1:
                                bug_status = bug_run.get("status", "?")
                                st.write(f"**BUG:** {bug_status}")
                            with b2:
                                gold_status = gold_run.get("status", "?")
                                st.write(f"**GOLD:** {gold_status}")
                            with b3:
                                color = "green" if label == "VALID" else "red"
                                st.markdown(f"**Label:** :{color}[{label}]")

                            if reason:
                                st.caption(reason)

                    # Diagnosis / failure classification
                    fc = attempt.get("failure_classification", {})
                    if fc:
                        fc_label = fc.get("label", "?")
                        fc_details = fc.get("details", "")
                        if fc_label != "success":
                            st.write(f"**Diagnosis:** {fc_label} - {fc_details}")

                    st.markdown("---")

    # --- Sub-section 3: Aggregate Summary ---
    summary = semantic_data.get("summary", {})
    if summary:
        st.markdown("#### Aggregate Summary")

        # Note/warning if present
        note = summary.get("note")
        if note:
            st.warning(note)

        # Extraction overview
        raw = summary.get("total_extracted_raw", 0)
        grounded = summary.get("grounded", summary.get("total_claims", 0))
        ungrounded_count = summary.get("ungrounded", 0)
        low_score_count = summary.get("low_score", 0)

        if raw > 0:
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                st.metric("Total Extracted (raw)", raw)
            with e2:
                st.metric("Grounded", grounded)
            with e3:
                st.metric("Ungrounded", ungrounded_count)
            with e4:
                st.metric("Low Score", low_score_count)

        # Test results
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Claims Tested", summary.get("total_claims", 0))
        with s2:
            st.metric("Validated (PASS)", summary.get("successful", 0))
        with s3:
            st.metric("Failed", summary.get("failed", 0))
        with s4:
            cvr = summary.get("cvr", 0)
            st.metric("CVR", f"{cvr:.0%}")

        # Label distribution from verification results
        label_dist = summary.get("label_distribution", {})
        if label_dist:
            st.markdown("**Label Distribution:**")
            label_cols = st.columns(len(label_dist))
            for col, (label, count) in zip(label_cols, label_dist.items()):
                with col:
                    st.metric(label, count)


# =========================================================================
# MAIN APP
# =========================================================================

st.title("E6 Verifier Harness")
st.markdown("Unified patch verification: static analysis, dynamic testing, and semantic claim verification")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Configuration")

mode = st.sidebar.radio(
    "Analysis Mode",
    ["SWE-bench Instance", "Custom Codebase"],
    help="Choose whether to test a SWE-bench instance or upload your own code"
)

st.sidebar.divider()

# --- Verification Layers ---
st.sidebar.subheader("Verification Layers")

enable_static = st.sidebar.checkbox("Static Analysis", value=True,
                                     help="Pylint, Flake8, Radon, Mypy, Bandit, AST validation")
enable_dynamic = st.sidebar.checkbox("Dynamic Analysis (SWE-bench tests)", value=True,
                                      help="Run FAIL_TO_PASS + PASS_TO_PASS tests in Singularity")

if mode == "Custom Codebase":
    enable_semantic = st.sidebar.checkbox(
        "Semantic Analysis", value=False, disabled=True,
        help="Requires SWE-bench instance (problem statement needed for claim extraction)"
    )
    st.sidebar.caption("Semantic analysis requires a SWE-bench instance.")
else:
    enable_semantic = st.sidebar.checkbox(
        "Semantic Analysis (claims + agentic loop)", value=False,
        help="LLM-based claim extraction, test generation via agentic loop, BUG vs GOLD verification"
    )

st.sidebar.divider()

# --- vLLM Configuration (only when semantic is enabled) ---
vllm_endpoint = os.environ.get("CLAIM_LLM_ENDPOINT", "http://127.0.0.1:8000/v1")
vllm_model = os.environ.get("CLAIM_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ")
vllm_api_key = None
max_claims = 6
max_attempts = 4

if enable_semantic:
    st.sidebar.subheader("vLLM Server")
    st.sidebar.info(
        "Start vLLM on a GPU node first, then enter the endpoint below.\n\n"
        "Example:\n```\n"
        "srun --gres=gpu:1 --mem=64G --pty bash\n"
        "python -m vllm.entrypoints.openai.api_server \\\n"
        "  --model Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \\\n"
        "  --host 0.0.0.0 --port 8000\n```"
    )

    vllm_endpoint = st.sidebar.text_input("vLLM Endpoint", value=vllm_endpoint)
    vllm_model = st.sidebar.text_input("Model Name", value=vllm_model)
    vllm_api_key_input = st.sidebar.text_input("API Key (optional)", type="password")
    if vllm_api_key_input:
        vllm_api_key = vllm_api_key_input

    # Test connection button
    if st.sidebar.button("Test Connection"):
        ok, msg = test_vllm_connection(vllm_endpoint)
        if ok:
            st.sidebar.success(msg)
            st.session_state.vllm_connected = True
        else:
            st.sidebar.error(msg)
            st.session_state.vllm_connected = False

    if st.session_state.vllm_connected:
        st.sidebar.success("vLLM: Connected")
    else:
        st.sidebar.warning("vLLM: Not connected. Click 'Test Connection' first.")

    st.sidebar.divider()
    max_claims = st.sidebar.slider("Max claims per instance", 1, 10, 6)
    max_attempts = st.sidebar.slider("Max attempts per claim", 1, 10, 4)

st.sidebar.divider()

# --- Container configuration ---
st.sidebar.subheader("Container Settings")
use_container = st.sidebar.checkbox(
    "Use Singularity Container",
    value=True,
    help="Run tests in isolated Singularity container (recommended)"
)

container_source = None
container_path = None
docker_image = None
container_file_path = None

if use_container:
    if mode == "SWE-bench Instance":
        st.sidebar.info("Container will be auto-built from SWE-bench instance")
        cached = list_cached_containers()
        if cached:
            st.sidebar.success(f"{len(cached)} cached containers available")
            with st.sidebar.expander("View Cache"):
                st.write(f"**Total cache size**: {sum(c['size_mb'] for c in cached):.1f} MB")
                for c in cached[:5]:
                    st.text(f"  {c['name'][:40]}")
    else:
        container_source = st.sidebar.radio(
            "Container Source",
            ["Browse Cache", "Docker Image", "Upload .sif", "None (Host)"],
            help="Choose how to provide the container"
        )

        if container_source == "Browse Cache":
            cached = list_cached_containers()
            if cached:
                st.sidebar.success(f"Found {len(cached)} cached containers")
                repos = {}
                for c in cached:
                    parts = Path(c['name']).stem.split('__')
                    repo = parts[0] if len(parts) > 0 else "other"
                    if repo not in repos:
                        repos[repo] = []
                    repos[repo].append(c)

                selected_repo = st.sidebar.selectbox("Repository", options=list(repos.keys()))
                repo_containers = repos[selected_repo]
                selected_container = st.sidebar.selectbox(
                    "Container",
                    options=range(len(repo_containers)),
                    format_func=lambda i: f"{repo_containers[i]['name']} ({repo_containers[i]['size_mb']:.0f}MB)"
                )
                container_file_path = repo_containers[selected_container]['path']
                st.sidebar.info(f"Using: {Path(container_file_path).name}")
            else:
                st.sidebar.warning("No cached containers found")
                container_source = "Docker Image"

        elif container_source == "Docker Image":
            docker_image = st.sidebar.text_input(
                "Docker Image",
                placeholder="python:3.9-slim",
                help="e.g., python:3.9, ubuntu:22.04"
            )
        elif container_source == "Upload .sif":
            container_file = st.sidebar.file_uploader(
                "Upload Singularity Image",
                type=['sif'],
                help="Upload a pre-built .sif file"
            )
            if container_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sif') as f:
                    f.write(container_file.read())
                    container_file_path = f.name
        elif container_source == "None (Host)":
            use_container = False


# =========================================================================
# Main content
# =========================================================================

if mode == "SWE-bench Instance":
    st.header("SWE-bench Instance Testing")

    col1, col2 = st.columns([3, 1])
    with col1:
        repo_filter = st.text_input(
            "Filter by repository",
            placeholder="e.g., scikit-learn/scikit-learn",
            help="Leave empty to show all repositories"
        )
    with col2:
        limit = st.number_input("Limit", 1, 100, 20, help="Maximum instances to load")

    if st.button("Load Instances", type="primary"):
        with st.spinner("Loading SWE-bench instances..."):
            try:
                loader = DatasetLoader("princeton-nlp/SWE-bench_Lite", hf_mode=True, split="test")
                instances = []
                for sample in loader.iter_samples(limit=limit, filter_repo=repo_filter or None):
                    instance_id = sample.get('metadata', {}).get('instance_id')
                    if instance_id:
                        instances.append({
                            'instance_id': instance_id,
                            'repo': sample.get('repo', 'unknown'),
                            'problem_statement': sample.get('problem_statement', '')[:200] + '...',
                            'patch': sample.get('patch', ''),
                            'sample': sample
                        })
                st.session_state.swebench_instances = instances
                st.success(f"Loaded {len(instances)} instances")
            except Exception as e:
                st.error(f"Failed to load instances: {e}")

    # Instance selection
    if 'swebench_instances' in st.session_state:
        instances = st.session_state.swebench_instances

        if instances:
            st.subheader(f"Select Instance ({len(instances)} available)")

            selected_idx = st.selectbox(
                "Choose an instance",
                range(len(instances)),
                format_func=lambda i: f"{instances[i]['instance_id']} - {instances[i]['repo']}"
            )
            selected_instance = instances[selected_idx]

            st.info(f"**Selected:** {selected_instance['instance_id']}")
            st.markdown(f"**Repository:** {selected_instance['repo']}")

            with st.expander("View Problem Statement"):
                st.write(selected_instance['problem_statement'])

            with st.expander("View Patch"):
                st.code(selected_instance['patch'], language='diff')

            # Check if semantic is enabled but vLLM not connected
            run_disabled = enable_semantic and not st.session_state.vllm_connected
            if run_disabled:
                st.warning("Semantic analysis is enabled but vLLM is not connected. "
                           "Use 'Test Connection' in the sidebar, or disable Semantic analysis.")

            # Run analysis button
            if st.button("Run Analysis", type="primary", disabled=run_disabled):
                st.write("---")
                st.header("Analysis Results")

                sample = selected_instance['sample']

                # Build layer set
                selected_layers = set()
                if enable_static:
                    selected_layers.add(Layer.STATIC)
                if enable_dynamic:
                    selected_layers.add(Layer.DYNAMIC)
                if enable_semantic:
                    selected_layers.add(Layer.SEMANTIC)

                if not selected_layers:
                    st.warning("No verification layers selected. Check at least one in the sidebar.")
                else:
                    # Build config
                    vllm_config = VLLMConfig(
                        endpoint=vllm_endpoint,
                        model=vllm_model,
                        api_key=vllm_api_key,
                    )
                    pipeline_config = PipelineConfig(
                        layers=selected_layers,
                        vllm=vllm_config,
                        repos_root="repos_temp_pipeline",
                        max_claims=max_claims,
                        max_attempts_per_claim=max_attempts,
                    )

                    # Run pipeline
                    callback = StreamlitCallback()
                    try:
                        report = run_pipeline(sample, pipeline_config, callback)
                        callback.done(report.overall_success)

                        # Store for history
                        st.session_state.analysis_results.append(report.to_dict())

                        # --- Dashboard ---
                        display_aggregated_dashboard(report)

                        st.divider()

                        # --- Per-layer detailed results ---
                        if Layer.STATIC in report.layers:
                            lr = report.layers[Layer.STATIC]
                            if lr.status == LayerStatus.SUCCESS and lr.data:
                                cq = lr.data.get("code_quality")
                                if cq:
                                    display_static_analysis(cq)
                                ss = lr.data.get("syntax_structure")
                                if ss:
                                    display_syntax_structure(ss)
                            elif lr.error:
                                st.error(f"Static layer error: {lr.error}")

                        if Layer.DYNAMIC in report.layers:
                            st.divider()
                            lr = report.layers[Layer.DYNAMIC]
                            if lr.status == LayerStatus.SUCCESS and lr.data:
                                display_test_results(lr.data)
                            elif lr.error:
                                st.error(f"Dynamic layer error: {lr.error}")

                        if Layer.SEMANTIC in report.layers:
                            st.divider()
                            lr = report.layers[Layer.SEMANTIC]
                            if lr.data:
                                if lr.error:
                                    st.warning(f"Semantic layer: {lr.error}")
                                display_semantic_results(lr.data)
                            elif lr.error:
                                st.error(f"Semantic layer error: {lr.error}")

                    except Exception as e:
                        callback.done(success=False)
                        st.error(f"Pipeline failed: {e}")
                        import traceback
                        st.code(traceback.format_exc(), language='text')

else:  # Custom Codebase
    st.header("Custom Codebase Testing")

    st.markdown("""
    Upload your codebase and patch to run static analysis and unit tests.

    **Requirements:**
    - Codebase should be a Git repository (zipped)
    - Patch should be in unified diff format
    - Repository should have tests (pytest or unittest)
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Upload Codebase")
        repo_zip = st.file_uploader(
            "Upload repository (ZIP)",
            type=['zip'],
            help="Upload a zipped Git repository"
        )

    with col2:
        st.subheader("2. Provide Patch")
        patch_input_method = st.radio(
            "Patch input method",
            ["Upload File", "Paste Text"]
        )

        if patch_input_method == "Upload File":
            patch_file = st.file_uploader(
                "Upload patch file",
                type=['diff', 'patch', 'txt']
            )
            patch_str = patch_file.read().decode('utf-8') if patch_file else None
        else:
            patch_str = st.text_area(
                "Paste patch (unified diff format)",
                height=200,
                placeholder="diff --git a/file.py b/file.py\n..."
            )

    st.subheader("3. Test Command (Optional)")
    test_command = st.text_input(
        "Custom test command",
        placeholder="e.g., python -m pytest tests/",
        help="Leave empty to auto-detect"
    )

    if st.button("Run Analysis", type="primary", disabled=not (repo_zip and patch_str)):
        st.write("---")
        st.header("Analysis Results")

        with st.spinner("Extracting repository..."):
            try:
                temp_dir = tempfile.mkdtemp(prefix="verifier_custom_")
                repo_path = Path(temp_dir) / "repo"
                repo_path.mkdir()

                import zipfile
                with zipfile.ZipFile(repo_zip) as zf:
                    zf.extractall(repo_path)

                st.success(f"Repository extracted to {repo_path}")

                # Find actual repo root
                git_dirs = list(repo_path.rglob('.git'))
                if git_dirs:
                    repo_path = git_dirs[0].parent
                    st.info(f"Found Git repository at: {repo_path}")

                # Apply patch
                st.write("Applying patch...")
                import subprocess
                patch_file_path = repo_path / ".temp_patch.diff"
                patch_file_path.write_text(patch_str)
                result = subprocess.run(
                    ["git", "apply", "--ignore-whitespace", str(patch_file_path)],
                    cwd=str(repo_path),
                    capture_output=True, text=True
                )
                patch_file_path.unlink(missing_ok=True)

                if result.returncode == 0:
                    st.success("Patch applied successfully")

                    # Build layer set (only static + dynamic for custom)
                    selected_layers = set()
                    if enable_static:
                        selected_layers.add(Layer.STATIC)
                    if enable_dynamic:
                        selected_layers.add(Layer.DYNAMIC)

                    if not selected_layers:
                        st.warning("No verification layers selected.")
                    else:
                        # For custom codebase, run static directly + dynamic if container available
                        # Static
                        if enable_static:
                            st.subheader("Static Analysis")
                            try:
                                static_results = run_static_analysis(str(repo_path), patch_str)
                                display_static_analysis(static_results)
                            except Exception as e:
                                st.error(f"Static analysis failed: {e}")

                        # Dynamic
                        if enable_dynamic:
                            st.divider()
                            st.subheader("Dynamic Analysis")

                            container_path_to_use = None
                            if use_container:
                                if docker_image:
                                    container_path_to_use = get_or_build_container(docker_image=docker_image)
                                elif container_file_path:
                                    container_path_to_use = get_or_build_container(container_file=container_file_path)

                            if container_path_to_use:
                                try:
                                    test_patch_singularity.install_package_in_singularity(
                                        repo_path=repo_path,
                                        image_path=str(container_path_to_use)
                                    )
                                    tests = []
                                    if test_command:
                                        tests = [test_command]
                                    test_result = test_patch_singularity.run_tests_in_singularity(
                                        repo_path=repo_path,
                                        tests=tests,
                                        image_path=str(container_path_to_use),
                                        collect_coverage=False,
                                        verbose=True
                                    )
                                    # Parse counts
                                    import re
                                    stdout = test_result.get('stdout', '')
                                    passed = int(m.group(1)) if (m := re.search(r'(\d+) passed', stdout)) else 0
                                    failed = int(m.group(1)) if (m := re.search(r'(\d+) failed', stdout)) else 0
                                    errors = int(m.group(1)) if (m := re.search(r'(\d+) error', stdout)) else 0
                                    display_test_results({
                                        'passed': passed, 'failed': failed, 'errors': errors,
                                        'total': passed + failed + errors,
                                        'stdout': stdout,
                                        'stderr': test_result.get('stderr', ''),
                                        'execution_mode': 'singularity',
                                        'container': str(container_path_to_use),
                                    })
                                except Exception as e:
                                    st.error(f"Dynamic analysis failed: {e}")
                            else:
                                st.warning("No container available. Provide a container for dynamic analysis.")

                else:
                    st.error("Failed to apply patch")

                shutil.rmtree(temp_dir, ignore_errors=True)

            except Exception as e:
                st.error(f"Analysis failed: {e}")
                import traceback
                st.code(traceback.format_exc(), language='text')

# ---------------------------------------------------------------------------
# Analysis History
# ---------------------------------------------------------------------------
if st.session_state.analysis_results:
    st.divider()
    st.header("Analysis History")

    st.write(f"Total analyses: {len(st.session_state.analysis_results)}")

    for i, result in enumerate(reversed(st.session_state.analysis_results)):
        with st.expander(f"Analysis {len(st.session_state.analysis_results) - i} - {result.get('timestamp', '?')}"):
            # Show summary
            summary_data = {
                'instance_id': result.get('instance_id', '?'),
                'repo': result.get('repo', '?'),
                'overall_success': result.get('overall_success', False),
                'layers_requested': result.get('layers_requested', []),
                'layers_completed': result.get('layers_completed', []),
            }
            # Add per-layer status + key metrics
            layers = result.get('layers', {})
            for layer_name, lr in layers.items():
                if isinstance(lr, dict):
                    layer_summary = {'status': lr.get('status', '?')}
                    data = lr.get('data', {})
                    if layer_name == Layer.STATIC and data:
                        cq = data.get('code_quality', {})
                        layer_summary['sqi'] = cq.get('sqi', {}).get('SQI', 0)
                    elif layer_name == Layer.DYNAMIC and data:
                        layer_summary['passed'] = data.get('passed', 0)
                        layer_summary['failed'] = data.get('failed', 0)
                        layer_summary['total'] = data.get('total', 0)
                    elif layer_name == Layer.SEMANTIC and data:
                        ext = data.get('extraction', {})
                        sm = data.get('summary', {})
                        layer_summary['claims_extracted_grounded'] = len(ext.get('claims', []))
                        layer_summary['claims_ungrounded'] = len(ext.get('ungrounded_claims', []))
                        layer_summary['claims_low_score'] = len(ext.get('low_score_claims', []))
                        note = sm.get('note')
                        if note:
                            layer_summary['note'] = note
                        layer_summary['total_tested'] = sm.get('total_claims', 0)
                        layer_summary['validated'] = sm.get('successful', 0)
                        layer_summary['cvr'] = sm.get('cvr', 0)
                        layer_summary['label_distribution'] = sm.get('label_distribution', {})

                        # Per-claim summary
                        claim_summaries = []
                        for cr in data.get('claim_loop_results', []):
                            cs = {
                                'claim_id': cr.get('claim_id', '?'),
                                'success': cr.get('success', False),
                                'attempts': len(cr.get('attempts', [])),
                                'failure_reason': cr.get('failure_reason'),
                            }
                            claim_summaries.append(cs)
                        layer_summary['claims'] = claim_summaries

                    summary_data[layer_name] = layer_summary
            st.json(summary_data)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    """
    **E6 Verifier Harness**

    Unified patch verification system featuring:
    - **Static Analysis**: Pylint, Flake8, Radon, Mypy, Bandit
    - **Dynamic Testing**: SWE-bench test execution (Singularity)
    - **Semantic Verification**: Claim extraction + agentic loop + BUG vs GOLD

    Supports both SWE-bench instances and custom codebases.
    """
)
