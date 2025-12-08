# SLURM Batch Job Usage Guide

## Overview

The fuzzing pipeline is designed for **CPU-only workloads** - no GPU needed! This guide shows how to run evaluations using SLURM batch jobs on your cluster.

### Why No GPU?

Our pipeline components:
- **Patch parsing** → CPU
- **Test generation** → CPU (string templates)
- **Test execution** → CPU (pytest in Singularity)
- **Coverage analysis** → CPU (JSON parsing)
- **Static analysis** → CPU (Pylint, Flake8)

**No LLM inference, no deep learning, no GPU acceleration needed!**

---

## Quick Start

### 1. Single Job (Small Dataset)

```bash
# Submit single job for up to ~100 patches
sbatch --export=PREDICTIONS_FILE=predictions.json slurm_jobs/run_fuzzing_single.slurm

# Check status
squeue -u $USER

# View output
tail -f logs/fuzzing_JOBID.out
```

### 2. Array Job (Large Dataset)

```bash
# Submit array job for 500+ patches (runs 10 tasks in parallel)
sbatch --export=PREDICTIONS_FILE=predictions.json,NUM_CHUNKS=10 \
    slurm_jobs/run_fuzzing_array.slurm

# Check progress
squeue -u $USER

# View specific task output
tail -f logs/fuzzing_JOBID_0.out
```

### 3. Merge Results

```bash
# After array job completes
python slurm_jobs/merge_results.py \
    --job-id 12345 \
    --output final_results.json \
    --summary
```

---

## Resource Requirements

### Per-Job Resources

| Resource | Value | Reason |
|----------|-------|--------|
| **CPUs** | 4 | Parallel test execution |
| **Memory** | 8GB | Singularity container + tests |
| **Time** | 12-24h | ~50 patches/hour |
| **GPU** | None | CPU-only workload |

### Scaling Guidelines

| Patches | Recommended Approach | Wall Time |
|---------|---------------------|-----------|
| 1-50 | Single job | 1-2 hours |
| 50-200 | Single job | 4-8 hours |
| 200-500 | Array job (10 tasks) | 2-4 hours |
| 500+ | Array job (20+ tasks) | 2-6 hours |

---

## Job Scripts

### Script 1: Single Job

**File:** `slurm_jobs/run_fuzzing_single.slurm`

```bash
sbatch --export=PREDICTIONS_FILE=my_preds.json \
    slurm_jobs/run_fuzzing_single.slurm
```

**Use cases:**
- Small datasets (<200 patches)
- Testing/debugging
- Quick evaluation

**Output:**
- `results/fuzzing_JOBID.json`
- `logs/fuzzing_JOBID.out`
- `logs/fuzzing_JOBID.err`

### Script 2: Array Job

**File:** `slurm_jobs/run_fuzzing_array.slurm`

```bash
# Process 500 patches using 10 parallel tasks
sbatch --export=PREDICTIONS_FILE=predictions.json,NUM_CHUNKS=10 \
    slurm_jobs/run_fuzzing_array.slurm
```

**Use cases:**
- Large datasets (200+ patches)
- Faster turnaround
- Production evaluation

**Output:**
- `results/fuzzing_JOBID_task0.json`
- `results/fuzzing_JOBID_task1.json`
- ...
- `results/fuzzing_JOBID_task9.json`

**Features:**
- `--array=0-9%5` limits to 5 concurrent tasks
- Automatic splitting of predictions
- Independent task execution
- Fault tolerance (tasks can fail independently)

---

## Workflow

### Complete Workflow Example

```bash
# 1. Prepare environment
cd /fs/nexus-scratch/ihbas/verifier_harness
conda activate verifier_fuzzing

# 2. Ensure Singularity image exists
python test_singularity_build.py

# 3. Prepare predictions file
# predictions.json should contain:
# [
#   {"instance_id": "django-001", "model_patch": "diff ...", ...},
#   ...
# ]

# 4. Submit array job
JOB_ID=$(sbatch --export=PREDICTIONS_FILE=predictions.json,NUM_CHUNKS=10 \
    slurm_jobs/run_fuzzing_array.slurm | awk '{print $4}')

echo "Submitted job: $JOB_ID"

# 5. Monitor progress
watch -n 10 "squeue -u $USER"

# 6. Check task outputs
tail -f logs/fuzzing_${JOB_ID}_0.out

# 7. After completion, merge results
python slurm_jobs/merge_results.py \
    --job-id $JOB_ID \
    --output results/final_results.json \
    --summary

# 8. Analyze results
python - << 'EOF'
import json
with open('results/final_results.json') as f:
    data = json.load(f)

summary = data['summary']
print(f"Total: {summary['total_patches']}")
print(f"Accept: {summary['accept_rate']:.1%}")
print(f"Reject: {summary['reject_rate']:.1%}")
EOF
```

---

## Configuration

### Customizing Job Parameters

Edit the `#SBATCH` directives at the top of the scripts:

```bash
#SBATCH --cpus-per-task=4     # Increase for faster test execution
#SBATCH --mem=8G              # Increase if out-of-memory errors
#SBATCH --time=24:00:00       # Adjust based on dataset size
#SBATCH --partition=general   # Change to your cluster's partition
#SBATCH --array=0-9%5         # Change array size and concurrency limit
```

### Customizing Evaluation Parameters

Edit the `python scripts/eval_cli.py` command:

```bash
python scripts/eval_cli.py \
    --predictions "$PREDICTIONS_FILE" \
    --dataset "princeton-nlp/SWE-bench_Verified" \  # Change dataset
    --output "results/fuzzing_${SLURM_JOB_ID}.json" \
    --timeout 180 \              # Increase for slow tests (seconds)
    --static-threshold 0.5 \     # Adjust quality threshold
    --coverage-threshold 0.5 \   # Adjust coverage threshold
    --verbose                    # Remove for less output
```

---

## Monitoring

### Check Job Status

```bash
# All your jobs
squeue -u $USER

# Specific job
squeue -j JOBID

# Detailed job info
scontrol show job JOBID

# Job history
sacct -j JOBID --format=JobID,JobName,Partition,State,Elapsed,MaxRSS
```

### View Logs in Real-Time

```bash
# Single job
tail -f logs/fuzzing_JOBID.out

# Array job - all tasks
tail -f logs/fuzzing_JOBID_*.out

# Array job - specific task
tail -f logs/fuzzing_JOBID_3.out
```

### Check Progress

```bash
# Count completed predictions in output
grep -c "Evaluating prediction" logs/fuzzing_JOBID.out

# Check for errors
grep -i "error\|failed" logs/fuzzing_JOBID.err

# Check current patch being processed
tail -n 20 logs/fuzzing_JOBID.out | grep "instance_id"
```

---

## Troubleshooting

### Common Issues

#### 1. Job Pending (PD state)

```bash
# Check why job is pending
squeue -j JOBID -o "%.18i %.9P %.8j %.8u %.2t %.10M %.6D %R"

# Common reasons:
# - Resources: Waiting for CPUs/memory
# - Priority: Other jobs have higher priority
# - Partition: Wrong partition specified
```

**Solution:** Wait, or reduce resource requests

#### 2. Job Failed Immediately

```bash
# Check error log
cat logs/fuzzing_JOBID.err

# Common issues:
# - Conda environment not activated
# - Singularity image not found
# - Predictions file not found
```

**Solution:**
```bash
# Verify environment
conda env list

# Verify image
ls -lh /scratch0/ihbas/.containers/singularity/verifier-swebench.sif

# Verify predictions file
ls -lh predictions.json
```

#### 3. Out of Memory

```bash
# Check memory usage
sacct -j JOBID --format=JobID,MaxRSS,ReqMem

# If MaxRSS > 8GB:
```

**Solution:** Increase memory in SLURM script:
```bash
#SBATCH --mem=16G  # Double the memory
```

#### 4. Timeout

```bash
# Check elapsed time
sacct -j JOBID --format=JobID,Elapsed,Timelimit
```

**Solution:** Increase time limit:
```bash
#SBATCH --time=48:00:00  # Increase to 48 hours
```

#### 5. Array Job: Some Tasks Failed

```bash
# Check which tasks failed
sacct -j JOBID --format=JobID,State | grep FAILED

# Example output:
# JOBID_3    FAILED
# JOBID_7    FAILED
```

**Solution:** Rerun failed tasks:
```bash
# Rerun specific tasks
sbatch --export=PREDICTIONS_FILE=chunks/chunk_3.json \
    slurm_jobs/run_fuzzing_single.slurm

sbatch --export=PREDICTIONS_FILE=chunks/chunk_7.json \
    slurm_jobs/run_fuzzing_single.slurm
```

---

## Advanced Usage

### Custom Array Sizes

```bash
# Process with 20 parallel tasks
sbatch --export=PREDICTIONS_FILE=predictions.json,NUM_CHUNKS=20 \
    --array=0-19%10 \
    slurm_jobs/run_fuzzing_array.slurm
```

### Priority Scheduling

```bash
# Run with higher priority (if allowed)
sbatch --nice=100 --export=PREDICTIONS_FILE=predictions.json \
    slurm_jobs/run_fuzzing_single.slurm
```

### Dependency Chains

```bash
# Submit job that waits for previous job to complete
JOB1=$(sbatch slurm_jobs/run_fuzzing_array.slurm | awk '{print $4}')

# Submit merge job that depends on JOB1
sbatch --dependency=afterok:$JOB1 merge_job.slurm
```

### Email Notifications

Add to SLURM script:
```bash
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=your.email@example.com
```

---

## Performance Optimization

### 1. Tune CPU Count

```bash
# More CPUs = faster pytest execution
#SBATCH --cpus-per-task=8  # Try 8 CPUs

# pytest will use multiple cores with pytest-xdist
```

### 2. Adjust Timeout

```bash
# Reduce timeout for faster feedback (if tests are simple)
python scripts/eval_cli.py ... --timeout 60  # 60 seconds

# Increase for complex tests
python scripts/eval_cli.py ... --timeout 300  # 5 minutes
```

### 3. Batch Size

```bash
# Smaller chunks = better parallelization but more overhead
NUM_CHUNKS=20  # 20 smaller chunks

# Larger chunks = less overhead but less parallelization
NUM_CHUNKS=5   # 5 larger chunks
```

### 4. Skip Static Analysis (if needed)

```bash
# For faster evaluation, skip static checks
python scripts/eval_cli.py ... --no-static
```

---

## Example: Complete SWE-bench Evaluation

### Scenario: Evaluate 500 patches from SWE-bench Verified

```bash
#!/bin/bash
# complete_evaluation.sh

set -e

echo "=== SWE-bench Fuzzing Evaluation ==="

# 1. Setup
cd /fs/nexus-scratch/ihbas/verifier_harness
conda activate verifier_fuzzing

# 2. Verify prerequisites
echo "Checking prerequisites..."
python - << 'EOF'
import sys
from pathlib import Path

# Check Singularity image
image = Path("/scratch0/ihbas/.containers/singularity/verifier-swebench.sif")
if not image.exists():
    print("ERROR: Singularity image not found")
    sys.exit(1)

# Check predictions file
preds = Path("predictions.json")
if not preds.exists():
    print("ERROR: predictions.json not found")
    sys.exit(1)

print("✓ Prerequisites OK")
EOF

# 3. Submit array job (500 patches / 20 chunks = 25 patches per task)
echo "Submitting SLURM array job..."
JOB_ID=$(sbatch \
    --export=PREDICTIONS_FILE=predictions.json,NUM_CHUNKS=20 \
    slurm_jobs/run_fuzzing_array.slurm | awk '{print $4}')

echo "✓ Job submitted: $JOB_ID"
echo "  Logs: logs/fuzzing_${JOB_ID}_*.out"
echo "  Results: results/fuzzing_${JOB_ID}_task*.json"

# 4. Wait for completion
echo "Waiting for job to complete..."
while squeue -j $JOB_ID -h > /dev/null 2>&1; do
    sleep 60
    echo "  Still running... ($(date))"
done

# 5. Merge results
echo "Merging results..."
python slurm_jobs/merge_results.py \
    --job-id $JOB_ID \
    --output results/swebench_fuzzing_results.json \
    --summary

echo "✓ Complete! Results in: results/swebench_fuzzing_results.json"
```

---

## Summary

**Key Points:**
- ✅ **CPU-only workload** - no GPU needed
- ✅ **Scalable** - single job or array jobs
- ✅ **Fault-tolerant** - tasks run independently
- ✅ **Efficient** - ~50 patches/hour per task
- ✅ **Easy to use** - just submit with sbatch

**Resource Allocation:**
- 4 CPUs, 8GB RAM per task
- No GPU
- 12-24 hour time limit

**For questions:** See `FUZZING_GUIDE.md` for detailed pipeline documentation.
