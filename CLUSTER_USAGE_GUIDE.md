# 🚀 Cluster Computing Guide - Integrated Pipeline

**Scale your verification pipeline across multiple repos and samples using SLURM cluster computing.**

---

## 📋 Overview

This guide helps you run the integrated pipeline (Static + Fuzzing + Rules) on hundreds of SWE-bench instances using SLURM array jobs with **intelligent storage management**.

### Key Features

✅ **Multi-repo support** - Process instances from different repositories
✅ **Smart storage management** - Automatic disk space monitoring and cleanup
✅ **Container reuse** - Cached containers shared across all jobs
✅ **Parallel execution** - Configurable concurrency (max 3-10 jobs recommended)
✅ **Modular analysis** - Enable/disable Static, Fuzzing, or Rules

### Storage Strategy

- **Containers are cached** at `/fs/nexus-scratch/ihbas/.cache/swebench_singularity/`
- Each container is **~1.2 GB** (unique per repo version)
- **Containers are reused** once built (< 1 second load time)
- You have **23 GB free** → Can store ~19 containers
- **Cleanup tools** help manage space for large batches

---

## 🎯 Quick Start

### 1. Single Repository (10 instances)

```bash
python submit_integrated_batch.py \
    --repo "scikit-learn/scikit-learn" \
    --limit 10 \
    --max-parallel 3
```

**Expected:**
- 10 jobs submitted
- Max 3 running simultaneously
- ~4 hours per job
- ~13 GB storage needed (if all containers are unique)

---

### 2. Multiple Repositories (50 instances)

```bash
python submit_integrated_batch.py \
    --limit 50 \
    --max-parallel 5
```

**Expected:**
- 50 jobs from various repos
- Max 5 running simultaneously
- Storage check will warn if space is insufficient

---

### 3. Custom Instance List

```bash
# Create your list
cat > my_instances.txt <<EOF
scikit-learn__scikit-learn-10297
pytest-dev__pytest-5413
django__django-11019
EOF

# Submit
python submit_integrated_batch.py \
    --instance-file my_instances.txt \
    --max-parallel 3
```

---

### 4. Dry Run (Check Before Submitting)

```bash
python submit_integrated_batch.py \
    --repo "django/django" \
    --limit 20 \
    --dry-run
```

Shows what will happen **without** actually submitting jobs.

---

## 📊 Storage Management

### Check Current Status

```bash
python slurm_cleanup_cache.py --status
```

**Output:**
```
======================================================================
Container Cache Status
======================================================================

Disk Usage:
  Total: 200.0 GB
  Used: 177.0 GB (89%)
  Available: 23.0 GB
  ⚠️  Disk space getting low

Cached Containers: 1
  Total size: 1.3 GB
  Average size: 1.3 GB

Most Recently Accessed:
  - scikit-learn__scikit-learn-10297: 1234.5 MB (0 days ago)
```

---

### Cleanup Strategies

#### Option 1: Keep N Most Recent Containers

```bash
# Keep only 10 most recently used containers
python slurm_cleanup_cache.py --keep-recent 10

# With dry-run to preview
python slurm_cleanup_cache.py --keep-recent 10 --dry-run
```

**Use when:** Processing many repos sequentially, need to limit cache size.

---

#### Option 2: Remove Old Containers

```bash
# Remove containers not accessed in 30 days
python slurm_cleanup_cache.py --cleanup-age 30

# More aggressive: 7 days
python slurm_cleanup_cache.py --cleanup-age 7
```

**Use when:** Have old containers from previous experiments.

---

#### Option 3: Free Space to Target

```bash
# Free up space until 15 GB is available
python slurm_cleanup_cache.py --free-space 15
```

**Use when:** Need a specific amount of free space for upcoming batch.

---

## 🔧 Advanced Configuration

### Disable Specific Modules (Faster Execution)

```bash
# Static only (fast, ~1 minute per instance)
python submit_integrated_batch.py \
    --repo "pytest-dev/pytest" \
    --limit 20 \
    --disable-fuzzing \
    --disable-rules \
    --max-parallel 10

# Fuzzing + Rules only (skip static)
python submit_integrated_batch.py \
    --limit 30 \
    --disable-static \
    --max-parallel 5
```

**Time estimates:**
- **Full pipeline**: ~3-4 hours per instance
- **Static only**: ~1 minute per instance
- **Fuzzing only**: ~3-4 hours per instance
- **Rules only**: ~30 seconds per instance

---

### Adjust Resource Allocation

Edit `slurm_integrated_pipeline.sh`:

```bash
#SBATCH --time=04:00:00      # 4 hours (adjust if needed)
#SBATCH --mem=16G            # 16 GB RAM (increase for large repos)
#SBATCH --cpus-per-task=4    # 4 CPUs (good for fuzzing)
```

**When to increase:**
- **Time**: Large repos (e.g., Django) may need 6-8 hours
- **Memory**: Complex static analysis may need 24-32 GB
- **CPUs**: More cores can speed up fuzzing slightly

---

## 📈 Monitoring Jobs

### View Running Jobs

```bash
# All your jobs
squeue -u $USER

# Specific job array
squeue -j <JOB_ID>
```

**Output:**
```
JOBID   PARTITION   NAME                USER    ST  TIME  NODES
123456_1   scavenger  integrated_pipeline  ihbas   R   0:45  1
123456_2   scavenger  integrated_pipeline  ihbas   R   0:32  1
123456_3   scavenger  integrated_pipeline  ihbas   R   0:28  1
```

---

### Watch Logs in Real-Time

```bash
# Watch a specific job
tail -f logs/pipeline_<JOB_ID>_<ARRAY_TASK_ID>.out

# Watch all jobs
tail -f logs/pipeline_*.out
```

---

### Check Results

```bash
# List completed results
ls -lh results/

# View specific result
cat results/scikit-learn__scikit-learn-10297.json

# Count completed vs failed
jq -r '.verdict' results/*.json | sort | uniq -c
```

**Example output:**
```
  15 ✅ EXCELLENT
  23 ✓ GOOD
  8 ⚠️ WARNING
  4 ❌ REJECT
```

---

### Cancel Jobs

```bash
# Cancel entire array
scancel <JOB_ID>

# Cancel specific task in array
scancel <JOB_ID>_<ARRAY_TASK_ID>

# Cancel all your jobs
scancel -u $USER
```

---

## 🎯 Recommended Workflows

### Workflow 1: Multi-Repo Testing (50-100 instances)

**Goal:** Test patches across different repositories

```bash
# Step 1: Check storage and get instance breakdown
python submit_integrated_batch.py --limit 100 --dry-run

# Step 2: If storage OK, submit with conservative parallelism
python submit_integrated_batch.py --limit 100 --max-parallel 5

# Step 3: Monitor storage during execution
watch -n 300 'python slurm_cleanup_cache.py --status'

# Step 4: If space runs low, cleanup old containers
python slurm_cleanup_cache.py --free-space 15
```

---

### Workflow 2: Single Repo Deep Dive (All instances)

**Goal:** Test all patches for a specific repository

```bash
# Step 1: Get instance count
python submit_integrated_batch.py \
    --repo "scikit-learn/scikit-learn" \
    --dry-run

# Step 2: Submit with higher parallelism (same repo, container reused)
python submit_integrated_batch.py \
    --repo "scikit-learn/scikit-learn" \
    --max-parallel 8
```

**Why higher parallelism?** Same repo = same container = no storage multiplier.

---

### Workflow 3: Fast Pre-screening (Static Only)

**Goal:** Quickly filter patches before expensive fuzzing

```bash
# Phase 1: Static analysis only (fast)
python submit_integrated_batch.py \
    --limit 200 \
    --disable-fuzzing \
    --disable-rules \
    --max-parallel 15

# Phase 2: Full analysis on high-scoring patches
# (Manually create list from Phase 1 results)
python submit_integrated_batch.py \
    --instance-file high_scoring.txt \
    --max-parallel 5
```

---

## 🔍 Troubleshooting

### Issue: "No space left on device"

**Solution:**
```bash
# Immediate cleanup
python slurm_cleanup_cache.py --keep-recent 5

# Check what was freed
python slurm_cleanup_cache.py --status
```

---

### Issue: Jobs timing out (4 hours not enough)

**Solution:** Edit `slurm_integrated_pipeline.sh`:
```bash
#SBATCH --time=08:00:00  # Increase to 8 hours
```

Then resubmit.

---

### Issue: Jobs failing with "Instance not found"

**Cause:** `instance_ids.txt` and array indices don't match

**Solution:**
```bash
# Verify file has correct number of lines
wc -l instance_ids.txt

# Resubmit with correct array spec
sbatch --array=1-<LINE_COUNT>%5 slurm_integrated_pipeline.sh
```

---

### Issue: Want to process 500+ instances but limited storage

**Solution - Staged Batches:**
```bash
# Batch 1: First 100
python submit_integrated_batch.py --limit 100 --max-parallel 5
# Wait for completion, then cleanup
python slurm_cleanup_cache.py --keep-recent 3

# Batch 2: Next 100 (skip first 100)
python submit_integrated_batch.py --skip 100 --limit 100 --max-parallel 5
# Cleanup again
python slurm_cleanup_cache.py --keep-recent 3

# Repeat...
```

---

## 📊 Performance & Cost Estimates

### Resource Usage per Instance

| Module | Time | Memory | Storage |
|--------|------|--------|---------|
| **Static** | ~1 min | ~4 GB | 0 GB |
| **Fuzzing** | ~3-4 hrs | ~12 GB | 0 GB |
| **Rules** | ~30 sec | ~2 GB | 0 GB |
| **Container** | ~1 hr (first time) | ~4 GB | ~1.2 GB |
| **Combined** | ~4 hrs | ~16 GB | ~1.2 GB |

### Parallelism Guidelines

| Scenario | Max Parallel | Reason |
|----------|--------------|--------|
| **Single repo** | 8-10 | Container reused, no storage issue |
| **Multi-repo** | 3-5 | Each job may need new container |
| **Static only** | 15-20 | Very light on resources |
| **Full pipeline** | 5-8 | Balance between speed and resources |

### Storage Planning

| Instances | Estimated Unique Containers | Storage Needed |
|-----------|---------------------------|----------------|
| 10 | ~8 | ~10 GB |
| 50 | ~40 | ~48 GB ⚠️ |
| 100 | ~80 | ~96 GB ⚠️⚠️ |

**Recommendation:** For >20 instances across repos, use staged batches with cleanup.

---

## 🎓 Best Practices

1. **Always dry-run first** - Understand what will happen
   ```bash
   python submit_integrated_batch.py <args> --dry-run
   ```

2. **Monitor storage during execution**
   ```bash
   watch -n 300 'df -h /fs/nexus-scratch'
   ```

3. **Start with small batches** - Test with 5-10 instances first

4. **Use container reuse** - Group jobs by repository when possible

5. **Cleanup between batches** - Keep only recent containers
   ```bash
   python slurm_cleanup_cache.py --keep-recent 10
   ```

6. **Check logs early** - Catch issues before 50 jobs fail
   ```bash
   tail -f logs/pipeline_*.out | grep -E '(ERROR|✗|Failed)'
   ```

---

## 📝 Summary

### To run on cluster:

```bash
# 1. Submit batch
python submit_integrated_batch.py --repo "your/repo" --limit 20 --max-parallel 3

# 2. Monitor
squeue -u $USER
tail -f logs/pipeline_*.out

# 3. Check results
ls -lh results/
jq -r '.verdict' results/*.json | sort | uniq -c

# 4. Cleanup if needed
python slurm_cleanup_cache.py --keep-recent 10
```

### Storage is your main constraint:
- **23 GB free** → ~19 containers
- **Each unique repo version** = 1 container (~1.2 GB)
- **Use cleanup tools** to manage space
- **Process in batches** for large-scale testing

---

**Happy testing! 🚀**
