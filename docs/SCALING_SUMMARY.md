# 🎯 Scaling Your Pipeline - Complete Solution

## Overview

You asked: **"How can I test more samples and repositories?"**

**Answer:** You now have **3 approaches** to scale your integrated pipeline:

---

## ✅ Approach 1: Python Batch Script (Simple)

**File:** `batch_integrated_pipeline.py` (not created yet - you cancelled it)

**When to use:**
- Running on a single machine
- Want sequential or basic parallel processing
- Don't need SLURM cluster features

**How to use:**
```bash
python batch_integrated_pipeline.py --repo "scikit-learn/scikit-learn" --limit 20
```

**Pros:**
- Simple, easy to understand
- No SLURM knowledge needed
- Good for small batches (5-20 instances)

**Cons:**
- No cluster parallelism
- Must manage storage manually
- Slower for large batches

---

## ✅ Approach 2: SLURM Cluster (Recommended for Large Scale) 🚀

**Files created:**
- `scripts/slurm/slurm_integrated_pipeline.sh` - Main SLURM batch script
- `scripts/slurm/slurm_worker_integrated.py` - Worker for single instance
- `scripts/submit_integrated_batch.py` - Smart submission helper
- `scripts/slurm/slurm_cleanup_cache.py` - Storage management

**When to use:**
- Need to process many instances (20-100+)
- Want parallel execution across cluster nodes
- Testing multiple repositories
- **This is what you should use for production**

**How to use:**
```bash
# Quick start
python scripts/submit_integrated_batch.py --repo "scikit-learn/scikit-learn" --limit 10 --max-parallel 3

# Check before running
python scripts/submit_integrated_batch.py --limit 50 --dry-run

# Multi-repo batch
python scripts/submit_integrated_batch.py --limit 100 --max-parallel 5
```

**Pros:**
- ✅ Parallel execution (3-10 jobs at once)
- ✅ Automatic storage management
- ✅ Container reuse across jobs
- ✅ Can process hundreds of instances
- ✅ Built-in monitoring and cleanup tools

**Cons:**
- Requires SLURM cluster access
- Storage is still limited (23 GB = ~19 containers)

---

## ✅ Approach 3: Notebook → Script Conversion

**Existing:** `integrated_pipeline_modular.ipynb`

**Convert to script:**
```bash
jupyter nbconvert --to script integrated_pipeline_modular.ipynb
# Then wrap in a loop for multiple instances
```

**When to use:**
- Quick experimentation
- One-off testing
- Interactive development

---

## 🎯 Recommendation: Use SLURM Cluster Approach

Based on your requirements, **Approach 2 (SLURM)** is best because:

1. **You have cluster access** (scavenger partition)
2. **Storage is managed** automatically
3. **Scales to 100+ instances** with batching
4. **Container reuse** means less storage needed
5. **All modules work** (Static + Fuzzing + Rules)

---

## 📊 Storage: The Real Constraint

You're right to worry about storage! Here's the reality:

### Current Situation
```
Free space: 23 GB
Current cache: 1.3 GB (1 container)
Container size: ~1.2 GB each
Maximum containers: ~19 (before running out)
```

### The Problem
- Each SWE-bench instance **may** need a unique container
- 100 instances = potentially 100 containers = **120 GB needed** ❌

### The Solution ✅

**1. Container Reuse**
- Multiple instances from the **same repo** share the same container
- Example: 10 scikit-learn instances = **1 container** (1.2 GB)

**2. Smart Cleanup** (automated in submission script)
```bash
# Automatic warning when space is low
python scripts/submit_integrated_batch.py --limit 50  # checks storage first

# Manual cleanup between batches
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 10
```

**3. Staged Batches**
```bash
# Process in chunks with cleanup between
python scripts/submit_integrated_batch.py --limit 50 --max-parallel 5
# Wait for completion, then cleanup
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 5

# Next batch
python scripts/submit_integrated_batch.py --skip 50 --limit 50 --max-parallel 5
```

---

## 🚀 Step-by-Step: Testing Multiple Repos

### Step 1: Start Small (Verify Everything Works)

```bash
# Test with 5 instances
python scripts/submit_integrated_batch.py --limit 5 --max-parallel 2

# Monitor
squeue -u $USER
tail -f logs/pipeline_*.out

# Check results
ls results/
```

**Expected time:** ~20 hours (5 × 4 hours)
**Expected storage:** ~6 GB (5 × 1.2 GB if all unique)

---

### Step 2: Medium Batch (20 instances)

```bash
# Check storage first
python scripts/submit_integrated_batch.py --limit 20 --dry-run

# Submit if OK
python scripts/submit_integrated_batch.py --limit 20 --max-parallel 5

# Monitor storage
watch -n 300 'python scripts/slurm/slurm_cleanup_cache.py --status'
```

**Expected time:** ~16 hours (20 instances, 5 parallel)
**Expected storage:** ~20-24 GB (may hit limit!)

---

### Step 3: Large Scale (100+ instances)

**Strategy: Staged batches with cleanup**

```bash
# Batch 1: First 50
python scripts/submit_integrated_batch.py --limit 50 --max-parallel 5
# Wait for completion (~40 hours)

# Cleanup (keep only 5 most recent)
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 5

# Batch 2: Next 50
python scripts/submit_integrated_batch.py --skip 50 --limit 50 --max-parallel 5

# Repeat as needed...
```

---

## 🎛️ Module Control for Speed

**Full pipeline is slow (3-4 hours per instance).** Speed it up by disabling modules:

### Static Only (Super Fast)
```bash
python scripts/submit_integrated_batch.py \
    --limit 100 \
    --disable-fuzzing \
    --disable-rules \
    --max-parallel 15
```
**Time:** ~100 minutes (100 × 1 min)

### Fuzzing + Rules (Skip Static)
```bash
python scripts/submit_integrated_batch.py \
    --limit 50 \
    --disable-static \
    --max-parallel 5
```
**Time:** Still ~200 hours, but no static overhead

---

## 📋 Quick Reference Commands

### Submit Jobs
```bash
# Single repo
python scripts/submit_integrated_batch.py --repo "pytest-dev/pytest" --limit 10 --max-parallel 3

# Multi-repo
python scripts/submit_integrated_batch.py --limit 50 --max-parallel 5

# Dry run first!
python scripts/submit_integrated_batch.py --limit 20 --dry-run
```

### Monitor
```bash
squeue -u $USER                           # View jobs
tail -f logs/pipeline_*.out               # Watch logs
python scripts/slurm/slurm_cleanup_cache.py --status    # Check storage
```

### Manage Storage
```bash
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 10     # Keep 10 newest
python scripts/slurm/slurm_cleanup_cache.py --free-space 15      # Free to 15 GB
python scripts/slurm/slurm_cleanup_cache.py --cleanup-age 30     # Remove old (30d)
```

### Check Results
```bash
ls -lh results/                                    # List results
cat results/<instance_id>.json                     # View result
jq -r '.verdict' results/*.json | sort | uniq -c  # Count verdicts
```

---

## 📚 Documentation

- **`CLUSTER_USAGE_GUIDE.md`** - Complete guide with examples
- **`CLUSTER_QUICK_REFERENCE.md`** - Command cheat sheet
- **`INTEGRATED_PIPELINE_GUIDE.md`** - Notebook usage guide

---

## 💡 Best Practices

1. ✅ **Always dry-run first** before submitting large batches
2. ✅ **Monitor storage** during execution
3. ✅ **Start small** (5-10 instances) to verify everything works
4. ✅ **Group by repo** when possible (container reuse)
5. ✅ **Use staged batches** for 100+ instances
6. ✅ **Cleanup between batches** to free space
7. ✅ **Disable modules you don't need** for faster results

---

## 🎯 Summary

**You asked about scaling to more samples/repos. Here's what you got:**

### ✅ SLURM Cluster System
- Parallel execution (3-10 jobs)
- Automatic storage monitoring
- Smart cleanup tools
- Container reuse
- Can scale to 100+ instances with batching

### ✅ Storage Management
- Check available space before running
- Automatic warnings when low
- Cleanup tools to free space
- Staged batch strategy for large scales

### ✅ Flexibility
- Enable/disable modules (Static/Fuzzing/Rules)
- Adjust parallelism based on resources
- Process single repos or multi-repo batches

### 🎯 Next Steps

1. **Test with 5 instances** to verify everything works:
   ```bash
   python scripts/submit_integrated_batch.py --limit 5 --max-parallel 2
   ```

2. **Scale up gradually** to 20, then 50, then 100+

3. **Use cleanup tools** to manage storage as you go

---

**You're ready to scale! 🚀**

Start with the Quick Reference and expand from there.
