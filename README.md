# Verification Harness for SWE-bench Patches

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

A unified verification system that evaluates AI-generated code patches using:

- **Static Analysis** - AST analysis, code quality metrics (Pylint, Flake8, Radon, Mypy, Bandit)
- **Dynamic Fuzzing** - Property-based testing with Hypothesis framework
- **Change-Aware Coverage** - Tests only modified lines (100x faster than full coverage)

**Status:** Production-ready for 194/500 SWE-bench instances (38.8%)

## Quick Start

```bash
# Automated setup (recommended)
./scripts/setup_fuzzing.sh

# Verify installation (build container only)
python scripts/run_swebench_instance.py --instance_id matplotlib__matplotlib-23314 --build-only

# Test single instance end-to-end
python scripts/run_swebench_instance.py --instance_id matplotlib__matplotlib-23314

# Run full evaluation
conda activate verifier_env
python scripts/submit_integrated_batch.py --limit 10 --max-parallel 3 --dry-run
```

## What This Does

Takes an AI-generated patch and runs it through:
1. **Static verification** - Code quality and structure analysis
2. **Dynamic fuzzing** - Generates property-based tests targeting changed code
3. **Isolated execution** - Runs tests in Singularity container
4. **Coverage analysis** - Measures test coverage of changes

**Output:** Verification report with pass/fail outcomes and coverage metrics

## Project Structure

```text
verifier_harness/
├── docs/                             # All guides & reports
│   ├── PIPELINE_OVERVIEW.md         # System overview
│   ├── CLEANUP_SUMMARY.md           # Recent repo cleanup notes
│   └── ...                          # Cluster + fuzzing guides
│
├── scripts/                          # Operational entry points
│   ├── setup_fuzzing.sh             # Automated environment setup
│   ├── eval_cli.py                  # CLI interface
│   ├── submit_integrated_batch.py   # Integrated SLURM submission
│   ├── run_swebench_instance.py     # Single-instance runner
│   ├── swebench_cache_manager.py    # Cache maintenance
│   └── slurm/                       # SLURM worker + helper scripts
│       └── slurm_integrated_pipeline.sh
│
├── verifier/                        # Core verification modules
├── swebench_integration/            # SWE-bench dataset utilities
├── slurm_jobs/                      # Predefined SLURM job specs
├── evaluation_pipeline.py           # Main orchestrator
└── tests/                           # Unit tests
```

## Performance

- **Speed:** ~45 seconds per patch
- **Throughput:** 500 patches/hour (10 parallel jobs)
- **Resources:** <500MB memory, 4 CPUs, no GPU
- **Cost:** $0 per patch (no LLM calls)


## Installation

### Prerequisites
- Python 3.9+
- Singularity (for HPC) or Docker (for local)
- Conda (recommended) or pip

### Setup

**Option 1: Automated (Recommended)**
```bash
git clone https://github.com/IgnacioHernandezBas/verifier_harness.git
cd verifier_harness
./scripts/setup_fuzzing.sh
```

**Option 2: Manual**
```bash
# Create conda environment
conda env create -f environment_linux.yml
conda activate verifier_env

# Or use pip
pip install -r requirements.txt

# Build container
python test_singularity_build.py
```

## Usage

### Single Instance
```bash
# Test specific SWE-bench instance
python scripts/eval_cli.py --instance-id matplotlib__matplotlib-23314
```

### Batch Processing (HPC)
```bash
# Submit SLURM job
sbatch slurm_jobs/run_fuzzing_single.slurm

# Or run array job for parallel processing
sbatch slurm_jobs/run_fuzzing_array.slurm
```

### Quick Verification
```bash
# Smoke-test with verbose logs
python scripts/run_swebench_instance.py --instance_id django__django-11001 --verbose

# Check batch submission without running jobs
python scripts/submit_integrated_batch.py --repo "django/django" --limit 5 --dry-run
```

## Supported Repositories

**Ready Now (194 instances):**
- matplotlib, scikit-learn, xarray, astropy, pytest, sphinx, pylint, requests, seaborn, flask

**Needs Test Path Detection (306 instances):**
- django (231), sympy (75)

See `REPOSITORY_COMPATIBILITY.md` for details.

## Documentation

| File | Purpose |
|------|---------|
| `README.md` | This file - quick start guide |
| `docs/FUZZING_IMPROVEMENTS_IMPLEMENTATION.md` | Comprehensive fuzzing guide |
| `docs/IMPLEMENTATION_SUMMARY.md` | Technical architecture |
| `docs/CLEANUP_SUMMARY.md` | Recent cleanup changes |
| `docs/SINGULARITY_USAGE.md` | Container operations |
| `docs/SLURM_USAGE.md` | HPC batch job guide |

## Troubleshooting

**Import errors:**
```bash
conda activate verifier_env
# or source venv/bin/activate
```

**Container not found:**
```bash
python test_singularity_build.py
```

**Dependencies missing:**
```bash
pip install -r requirements.txt
```

## Contributing

See `docs/IMPLEMENTATION_SUMMARY.md` for technical details and architecture.

## Recent Changes

Repository was recently cleaned up to remove redundant files and improve organization. See `docs/CLEANUP_SUMMARY.md` for details.

