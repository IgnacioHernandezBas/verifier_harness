# Technology Stack & Resources

## Overview

This document describes the full technology stack powering the Verifier Harness — a unified pipeline that evaluates AI-generated patches from SWE-bench using three complementary verification layers: **Static**, **Dynamic**, and **Semantic**. Results are surfaced through an interactive **Streamlit** dashboard.

---

## 1. Dataset

### SWE-bench Lite

| Property | Value |
|----------|-------|
| **Source** | [`princeton-nlp/SWE-bench_Lite`](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite) via HuggingFace Hub |
| **Total instances** | 500 |
| **Currently supported** | 194 (38.8%) — full static + dynamic + semantic pipeline |
| **Pending support** | 306 (django/sympy — test discovery improvements in progress) |
| **License** | MIT |

**Instance schema** (key fields):

| Field | Description |
|-------|-------------|
| `instance_id` | Unique identifier (e.g., `astropy__astropy-7746`) |
| `repo` | GitHub repository slug |
| `base_commit` | Parent commit the patch applies on top of |
| `patch` | The AI-generated code patch to evaluate |
| `test_patch` | Gold patch used for oracle validation |
| `problem_statement` | Original GitHub issue text |
| `test_cmd` | Shell command that runs the relevant test suite |
| `env_setup_commit` | Optional commit for environment reproducibility |

**Loading**: Handled by `swebench_integration/dataset_loader.py` using the HuggingFace `datasets` library (v4.1.1) with PyArrow-backed columnar caching.

---

## 2. Repositories Used

The 500 SWE-bench Lite instances span **13 major Python open-source projects**:

| Repository | Instances | Share | Category | Pipeline Status |
|------------|-----------|-------|----------|----------------|
| [django/django](https://github.com/django/django) | 231 | 46.2% | Pure Python, ORM | ⚠ In progress (test discovery) |
| [sympy/sympy](https://github.com/sympy/sympy) | 75 | 15.0% | C extensions | ⚠ In progress (build complexity) |
| [sphinx-doc/sphinx](https://github.com/sphinx-doc/sphinx) | 44 | 8.8% | C extensions | ✅ Supported |
| [matplotlib/matplotlib](https://github.com/matplotlib/matplotlib) | 34 | 6.8% | C extensions | ✅ Supported |
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 32 | 6.4% | Pure Python | ✅ Supported |
| [pydata/xarray](https://github.com/pydata/xarray) | 22 | 4.4% | setuptools_scm | ✅ Supported |
| [astropy/astropy](https://github.com/astropy/astropy) | 22 | 4.4% | C extensions | ✅ Supported |
| [pytest-dev/pytest](https://github.com/pytest-dev/pytest) | 19 | 3.8% | setuptools_scm | ✅ Supported |
| [PyCQA/pylint](https://github.com/PyCQA/pylint) | 10 | 2.0% | Pure Python | ✅ Supported |
| [psf/requests](https://github.com/psf/requests) | 8 | 1.6% | Pure Python | ✅ Supported |
| [mwaskom/seaborn](https://github.com/mwaskom/seaborn) | 2 | 0.4% | Pure Python | ✅ Supported |
| [pallets/flask](https://github.com/pallets/flask) | 1 | 0.2% | Pure Python | ✅ Supported |

> Each repository is cloned at the exact `base_commit` specified by the instance, ensuring reproducibility.

---

## 3. Models Used

All models are served via a **vLLM** inference server exposing an OpenAI-compatible REST API (`http://127.0.0.1:8000/v1`). Model configurations live in `claim_extraction/configs/`.

### 3.1 Claim Extraction Models

These models analyse the patch + GitHub issue and extract structured, verifiable claims about what the fix is supposed to do.

| Model | Size (active) | Quantization | VRAM | Config file | Use |
|-------|--------------|--------------|------|-------------|-----|
| **Qwen2.5-Coder-32B-Instruct** | 32B | AWQ 4-bit | ~19 GB | `claim_extraction.yaml` | **Default** — best code-reasoning / speed trade-off |
| **Qwen2.5-72B-Instruct** | 72B | AWQ 4-bit | ~38 GB | `claim_extraction_qwen72b.yaml` | Higher accuracy, 2× GPU required |
| **Meta-Llama-3.1-70B-Instruct** | 70B | AWQ INT4 | ~38 GB | `claim_extraction_llama70b.yaml` | Baseline comparison |
| **DeepSeek-Coder-V2-Instruct** | 21B active (236B MoE) | AWQ 4-bit | ~40 GB | `claim_extraction_deepseek_v2.yaml` | Complex multi-step reasoning |

**Key inference parameters** (from `claim_extraction.yaml`):

```yaml
llm:
  backend: vllm
  endpoint: http://127.0.0.1:8000/v1
  temperature: 0.1        # Near-deterministic for consistent claim extraction
  max_tokens: 2048
  timeout_s: 120
extraction:
  min_claim_score: 2
  max_claims_per_issue: 6
  require_grounding: true  # Claims must reference modified code lines
```

### 3.2 Agentic Loop Models

The closed-loop refinement pipeline (`agentic_closed_loop/`) uses the same vLLM backend to iteratively generate, execute, and repair property-based tests. Any model above can be swapped in via the factory (`claim_extraction/llm/factory.py`).

### 3.3 Prompt Engineering

Prompts are **Jinja2 templates** (`claim_extraction/prompts/`):

| Template | Strategy | Notes |
|----------|----------|-------|
| `claim_prompt_v2_1.jinja` | Zero-shot | Base extraction |
| `claim_prompt_v2_2.jinja` | Zero-shot + issue context | Higher grounding rate |

---

## 4. Verification Pipeline — Core Stack

### 4.1 Language & Runtime

| Component | Technology |
|-----------|-----------|
| Primary language | Python 3.11 (containers) / 3.9+ (local) |
| Package manager | pip + conda (`environment_linux.yml`) |
| Type checking | MyPy 1.18.2 |

### 4.2 Static Layer

| Tool | Version | Purpose |
|------|---------|---------|
| **Python `ast`** | stdlib | AST-based structural analysis |
| **Pylint** | 3.3.9 | Code quality scoring |
| **Flake8** | 7.3.0 | PEP 8 style compliance |
| **Radon** | 6.0.1 | Cyclomatic complexity + Maintainability Index |
| **MyPy** | 1.18.2 | Static type correctness |
| **Bandit** | 1.8.6 | Security vulnerability scanning (CWE mapping) |

Output: a **Static Quality Index (SQI)** score in [0, 1] aggregated across tools, plus per-file drill-down.

### 4.3 Dynamic Layer

| Tool | Version | Purpose |
|------|---------|---------|
| **pytest** | 8.4.2 | Test discovery & execution |
| **Hypothesis** | 6.140.3 | Property-based test generation |
| **coverage.py** | 7.10.7 | Change-aware line coverage |
| **pytest-cov** | 7.0.0 | pytest ↔ coverage.py bridge |
| **Atheris** | latest | Coverage-guided fuzzing (Clang/LLVM backend) |

**Change-aware coverage**: rather than computing full-repo coverage, the pipeline extracts only the lines touched by the patch from the unified diff, making coverage measurement ~100× faster.

### 4.4 Semantic Layer (9 Rules)

| Rule | Focus area | Bug taxonomy |
|------|-----------|-------------|
| Rule 1 | Boundary & intersection probing | CWE 241x–244x |
| Rule 2 | Predicate logic / MC/DC | CWE 312x, 244x |
| Rule 3 | State-transition tours | CWE 3154, 316x |
| Rule 4 | Definition–use execution | CWE 323x, 324x, 4232 |
| Rule 5 | Resource lifecycle under load | CWE 416x, 426x |
| Rule 6 | Robust exception handling | CWE 26xx, 25xx |
| Rule 7 | Transaction order validation | CWE 611x, 612x, 622x |
| Rule 8 | Structured input / conversion | CWE 4214, 422x, 4285 |
| Rule 9 | Concurrency & lock correctness | CWE 721x, 742x |

Each rule returns a `RuleResult` dataclass (`verifier/rules/base.py`) with `status`, `findings`, `metrics`, and a narrative `details` string.

---

## 5. Frontend — Streamlit Dashboard

**Streamlit** was chosen over React as the primary UI because:

- **Already integrated**: `streamlit/app.py` is present and operational in the repo.
- **Zero JS overhead**: the entire team works in Python; no frontend build toolchain is needed.
- **First-class data widgets**: native DataFrames, `st.metric`, `st.expander`, and direct Plotly/Altair rendering cover all dashboard needs.
- **Rapid iteration**: a new verification result view can go from idea to interactive chart in minutes.
- **Shared data models**: Streamlit runs in the same Python process that imports verification results — no REST serialisation layer required for local use.

| Library | Version | Role |
|---------|---------|------|
| **Streamlit** | 1.50.0 | Multi-page interactive dashboard |
| **Plotly** | 6.3.1 | Interactive bar/scatter/heatmap charts |
| **Altair** | 5.5.0 | Declarative statistical charts |
| **pandas** | 2.3.3 | Result aggregation and tabular display |

**Dashboard pages** (`streamlit/pages/`):

| Page | Content |
|------|---------|
| `static_verifier.py` | Per-file SQI breakdown, Pylint/Flake8/Radon metrics |
| `results_viewer.py` | Batch result explorer: filter by repo, rule, status |
| *(planned)* semantic explorer | Per-rule findings with source line highlighting |
| *(planned)* model comparison | Side-by-side claim extraction quality across models |

**Run**:
```bash
streamlit run streamlit/app.py
```

---

## 6. Infrastructure

### 6.1 Compute Cluster (Primary)

| Resource | Specification |
|----------|--------------|
| Scheduler | **SLURM** — job arrays for embarrassingly parallel instance evaluation |
| GPU nodes | 2× NVIDIA A6000 / L40S (48 GB VRAM each = 96 GB total) |
| Storage (models) | `/fs/cml-scratch/ihbas/cache/huggingface/hub/` (~97 GB for three quantized models) |
| Storage (containers) | `/fs/nexus-scratch/ihbas/.containers/singularity/` |

**SLURM job types** (`slurm_jobs/`):

| Script | Purpose |
|--------|---------|
| `run_fuzzing_single.slurm` | Single-instance evaluation |
| `run_fuzzing_array.slurm` | Array job over many instances |
| `slurm_integrated_verification.sbatch` | Full three-layer pipeline |
| `claim_extraction/scripts_slurm/extract_claims.sbatch` | LLM claim extraction job |

### 6.2 Containers

Two container runtimes are supported; **Singularity** is the default for HPC.

| Runtime | Use case | Definition |
|---------|---------|-----------|
| **Singularity** | HPC clusters (no root, no daemon) | `verifier-swebench.sif` |
| **Docker / Podman** | Local development | Derived from `python:3.11-slim` |

**Atheris fuzzer container** (`containers/atheris-fuzzer.def`):
- Base: Ubuntu 22.04
- Toolchain: Clang 14 + LLVM (required by Atheris for coverage instrumentation)
- Python: 3.11 with Atheris, coverage.py, pytest

**Container executors** (`verifier/dynamic_analyzers/`):

| Module | Runtime |
|--------|---------|
| `singularity_executor.py` | Singularity |
| `podman_executor.py` | Podman |
| `swebench_singularity_executor.py` | Singularity + SWE-bench test harness |

### 6.3 Distributed / Serverless (Optional)

| Tool | Version | Role |
|------|---------|------|
| **Modal** | 1.2.1 | Serverless GPU jobs for claim extraction without a dedicated cluster |
| **Ray** | — | Distributed task graph for large-scale batch runs |
| **joblib** | — | Local multiprocessing for small batches |

### 6.4 Model Serving

| Component | Technology |
|-----------|-----------|
| Inference server | **vLLM** (latest) — OpenAI-compatible HTTP API |
| Quantization | **AWQ** (Activation-aware Weight Quantization) — 4-bit, loaded by vLLM |
| Model registry | HuggingFace Hub (authenticated download at job start) |
| API endpoint | `http://127.0.0.1:8000/v1` (local) |

---

## 7. Developer Toolchain

| Tool | Version | Purpose |
|------|---------|---------|
| **Black** | 25.9.0 | Code formatting |
| **isort** | 6.1.0 | Import ordering |
| **pre-commit** | 4.3.0 | Git hooks |
| **Typer / Click** | 0.20.0 / 8.2.1 | CLI interfaces (`scripts/eval_cli.py`) |
| **Rich** | 14.1.0 | Terminal progress + structured output |
| **gitpython** | 3.1.45 | Programmatic git operations |
| **ghapi** | 1.0.8 | GitHub API (patch retrieval) |
| **Jinja2** | — | LLM prompt templating |
| **PyYAML** | — | Model/pipeline configuration |
| **Jupyter** | 6.30.1 | Exploratory analysis notebooks |

---

## 8. Dependency Management

| File | Scope |
|------|-------|
| `requirements.txt` | Full pip environment (157 packages) |
| `requirements_linux.txt` | Linux-specific overrides |
| `environment.yml` | Conda (Windows / macOS dev) |
| `environment_linux.yml` | Conda (Linux / HPC) |

---

## 9. Performance Reference

| Metric | Value |
|--------|-------|
| Time per patch (3 layers) | ~45 seconds |
| Throughput (10 parallel SLURM jobs) | ~500 patches / hour |
| Peak memory per worker | < 500 MB |
| GPU required for core pipeline | No (GPU needed only for LLM claim extraction) |
| Container startup overhead | ~2 seconds |
| HuggingFace model cache (3 models) | ~97 GB |

---

## 10. External APIs & Services

| Service | SDK / Library | Purpose |
|---------|--------------|---------|
| HuggingFace Hub | `datasets` 4.1.1, `huggingface_hub` | Dataset streaming, model download |
| GitHub REST API | `ghapi` 1.0.8 | Fetch raw patches, issue metadata |
| vLLM OpenAI API | `openai` Python client | LLM inference (claim extraction, test gen) |
