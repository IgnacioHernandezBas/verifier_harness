# Agentic Loop Results System

This directory contains tools for generating human-readable summaries of agentic loop test generation runs.

## Directory Structure

Results are organized by test generation model and claim extraction model:

```
agentic_closed_loop/results/
├── tests_Qwen2.5-Coder-32B-Instruct-AWQ/
│   ├── claims_Qwen2.5-Coder-32B-Instruct-AWQ/
│   │   ├── django__django-13321_C1_summary.json
│   │   ├── django__django-13321_C1_summary.txt
│   │   ├── astropy__astropy-7746_C1_summary.json
│   │   └── astropy__astropy-7746_C1_summary.txt
│   └── claims_DeepSeek-V3/
│       └── ...
├── tests_DeepSeek-V3/
│   └── claims_Qwen2.5-Coder-32B-Instruct-AWQ/
│       └── ...
└── summary_report.csv  # Aggregate CSV for all runs
```

## Automatic Generation

Summaries are **automatically generated** when the orchestrator completes a run (success or failure).

## Manual Generation

### Single Instance

Generate a summary for a specific state file:

```bash
python -m agentic_closed_loop.result_summarizer \
  --state-file agentic_closed_loop/state/django__django-13321_C1.json \
  --tests-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" \
  --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
```

### Batch Processing

Process all existing state files:

```bash
python -m agentic_closed_loop.batch_summarize_results \
  --state-dir agentic_closed_loop/state \
  --tests-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" \
  --claims-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
```

Process only specific instances:

```bash
python -m agentic_closed_loop.batch_summarize_results \
  --state-dir agentic_closed_loop/state \
  --tests-model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" \
  --pattern "django*_C1.json"
```

## Output Files

### JSON Summary (`{instance}_{claim}_summary.json`)

Machine-readable format containing:
- Instance and claim IDs
- Model information
- Status (success, non_discriminative, failed, etc.)
- Final verification results (bug/gold status)
- Iteration history
- File references

Example:
```json
{
  "instance_id": "django__django-13321",
  "claim_id": "C1",
  "status": "success",
  "total_attempts": 3,
  "final_result": {
    "discriminative": true,
    "classification": "VALID",
    "bug": "FAILED",
    "gold": "PASSED"
  },
  "iterations": [...]
}
```

### Text Summary (`{instance}_{claim}_summary.txt`)

Human-readable format for quick inspection:

```
================================================================================
AGENTIC LOOP SUMMARY
================================================================================
Instance:       django__django-13321
Claim:          C1
Tests Model:    Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
Claims Model:   Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
Timestamp:      2026-02-15 14:30:00
SLURM Job:      6270940

STATUS:         ✓ SUCCESS
Attempts:       3 / 4

FINAL RESULTS:
  Classification: VALID
  Bug:            FAILED
  Gold:           PASSED
  Discriminative: YES

ITERATION HISTORY:
  [1] GUARDRAIL FAILED
      signature_mismatch: Missing fixture 'settings'

  [2] VERIFICATION_COMPLETE
      NON_DISCRIMINATIVE: Bug=PASSED, Gold=PASSED

  [3] ✓ SUCCESS
      Bug=FAILED, Gold=PASSED

FILES:
  Test:         claim_test_generation/tests_out/.../test_claim_c1.py
  State:        agentic_closed_loop/state/django__django-13321_C1.json
  SLURM logs:   agentic_closed_loop/scripts_slurm/logs/agentic_hybrid_6270940.out
================================================================================
```

### CSV Summary (`summary_report.csv`)

Aggregate report for all runs, useful for batch analysis in Excel/Pandas:

```csv
instance_id,claim_id,tests_model,claims_model,status,discriminative,classification,attempts,bug,gold,failure_reason,timestamp,slurm_job_id
django__django-13321,C1,Qwen/Qwen2.5-Coder-32B-Instruct-AWQ,Qwen/Qwen2.5-Coder-32B-Instruct-AWQ,success,true,VALID,3,FAILED,PASSED,,2026-02-15T14:30:00,6270940
```

## Quick Analysis

### View all results for a model combination:
```bash
cat agentic_closed_loop/results/tests_Qwen2.5-Coder-32B-Instruct-AWQ/claims_Qwen2.5-Coder-32B-Instruct-AWQ/*.txt
```

### Find all successful runs:
```bash
grep "✓ SUCCESS" agentic_closed_loop/results/tests_*/claims_*/*.txt
```

### Count discriminative tests:
```bash
grep "Discriminative: YES" agentic_closed_loop/results/tests_*/claims_*/*.txt | wc -l
```

### Analysis with pandas:
```python
import pandas as pd

df = pd.read_csv('agentic_closed_loop/results/summary_report.csv')

# Success rate
success_rate = (df['status'] == 'success').mean()

# Discriminative rate
disc_rate = df['discriminative'].mean()

# Group by model
df.groupby(['tests_model', 'claims_model'])['discriminative'].mean()
```

## Status Values

- `success`: Discriminative test found (VALID)
- `non_discriminative`: Test doesn't distinguish bug from gold
- `failed`: Test has other issues (OVERCONSTRAINED, INVERTED, UNRESOLVED)
- `guardrail_failed`: Guardrail rejected the test plan
- `max_attempts`: Reached maximum iterations without success
- `stuck`: Same error repeated 3+ times
- `unknown`: Unable to determine status

## Classification Labels

From verification (bug vs gold):
- **VALID**: Bug=FAIL, Gold=PASS (discriminative ✓)
- **NON_DISCRIMINATIVE**: Both pass or both fail
- **OVERCONSTRAINED**: Both fail (test too strict)
- **INVERTED**: Bug=PASS, Gold=FAIL (logic backwards)
- **UNRESOLVED**: Error/timeout occurred
