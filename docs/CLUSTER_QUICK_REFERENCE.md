# 🚀 Cluster Computing - Quick Reference Card

## Essential Commands

### Submit Jobs

```bash
# Basic: 10 instances from one repo
python scripts/submit_integrated_batch.py --repo "scikit-learn/scikit-learn" --limit 10 --max-parallel 3

# Multi-repo: 50 instances
python scripts/submit_integrated_batch.py --limit 50 --max-parallel 5

# Custom list
python scripts/submit_integrated_batch.py --instance-file my_instances.txt --max-parallel 3

# Dry run (check first!)
python scripts/submit_integrated_batch.py --limit 20 --dry-run
```

---

## Monitoring

```bash
# View jobs
squeue -u $USER

# Watch logs
tail -f logs/pipeline_*.out

# Check results
ls -lh results/
cat results/<instance_id>.json

# Count verdicts
jq -r '.verdict' results/*.json | sort | uniq -c
```

---

## Storage Management

```bash
# Check status
python scripts/slurm/slurm_cleanup_cache.py --status

# Keep 10 most recent containers
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 10

# Remove containers older than 30 days
python scripts/slurm/slurm_cleanup_cache.py --cleanup-age 30

# Free up to 15 GB
python scripts/slurm/slurm_cleanup_cache.py --free-space 15

# Dry run first!
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 10 --dry-run
```

---

## Module Control

```bash
# All modules (default)
python scripts/submit_integrated_batch.py --limit 20 --max-parallel 3

# Static only (fast: ~1 min/instance)
python scripts/submit_integrated_batch.py --limit 50 --disable-fuzzing --disable-rules --max-parallel 10

# Fuzzing + Rules only
python scripts/submit_integrated_batch.py --limit 20 --disable-static --max-parallel 5

# Rules only (very fast: ~30 sec/instance)
python scripts/submit_integrated_batch.py --limit 100 --disable-static --disable-fuzzing --max-parallel 15
```

---

## Job Control

```bash
# Cancel all your jobs
scancel -u $USER

# Cancel specific job array
scancel <JOB_ID>

# Cancel one task
scancel <JOB_ID>_<ARRAY_TASK_ID>
```

---

## Storage Constraints

| Your System | Capacity |
|-------------|----------|
| **Free space** | 23 GB |
| **Containers per GB** | ~0.8 containers |
| **Max containers** | ~19 (without cleanup) |
| **Container size** | ~1.2 GB each |

**Rule of Thumb:** For N instances across different repos, need ~N × 0.8 × 1.2 GB = N GB of storage

---

## Common Workflows

### Workflow 1: Quick test (5 instances)

```bash
python scripts/submit_integrated_batch.py --repo "scikit-learn/scikit-learn" --limit 10 --max-parallel 3
```

---

### Workflow 2: Medium batch (20 instances)

```bash
# Check first
python scripts/submit_integrated_batch.py --limit 20 --dry-run

# Submit
python scripts/submit_integrated_batch.py --limit 20 --max-parallel 5

# Monitor storage
watch -n 300 'python scripts/slurm/slurm_cleanup_cache.py --status'
```

---

### Workflow 3: Large-scale (100+ instances)

```bash
# Batch 1
python scripts/submit_integrated_batch.py --limit 50 --max-parallel 5
# Wait for completion...

# Cleanup
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 5

# Batch 2
python scripts/submit_integrated_batch.py --skip 50 --limit 50 --max-parallel 5
```

---

## Timing Estimates

| Configuration | Time per Instance |
|--------------|-------------------|
| **Full pipeline** | 3-4 hours |
| **Static only** | 1 minute |
| **Fuzzing only** | 3-4 hours |
| **Rules only** | 30 seconds |

---

## Resource Allocation

Default (in `scripts/slurm/slurm_integrated_pipeline.sh`):
```bash
--time=04:00:00          # 4 hours
--mem=16G                # 16 GB RAM
--cpus-per-task=4        # 4 CPUs
--partition=scavenger    # Scavenger queue
```

---

## Emergency Commands

### Running out of space?

```bash
# Immediate cleanup (keep only 3 most recent)
python scripts/slurm/slurm_cleanup_cache.py --keep-recent 3

# Check results
python scripts/slurm/slurm_cleanup_cache.py --status
```

---

### Jobs stuck/failing?

```bash
# Check logs
tail -30 logs/pipeline_<JOB_ID>_<TASK_ID>.err

# Cancel and resubmit
scancel <JOB_ID>
python scripts/submit_integrated_batch.py <original args>
```

---

### Want to pause processing?

```bash
# Hold all pending jobs
scontrol hold <JOB_ID>

# Release when ready
scontrol release <JOB_ID>
```

---

## File Locations

```
verifier_harness/
├── logs/                          # SLURM output logs
│   └── pipeline_<JOB>_<TASK>.out
├── results/                       # JSON results
│   └── <instance_id>.json
├── instance_ids.txt               # Generated instance list
├── scripts/slurm/slurm_integrated_pipeline.sh   # Main SLURM script
├── scripts/slurm/slurm_worker_integrated.py     # Worker script
├── scripts/submit_integrated_batch.py     # Submission helper
└── scripts/slurm/slurm_cleanup_cache.py         # Storage management
```

**Container Cache:**
```
/fs/nexus-scratch/ihbas/.cache/swebench_singularity/
└── <repo>/
    └── <instance_id>.sif
```

---

## Result Format

```json
{
  "instance_id": "scikit-learn__scikit-learn-10297",
  "success": true,
  "overall_score": 80.6,
  "verdict": "✅ EXCELLENT",
  "reason": "All checks passed",
  "container_from_cache": true,
  "elapsed_seconds": 3245,
  "static": { "sqi_score": 62.1, "passed": true },
  "fuzzing": { "combined_coverage": 20.0, "passed": false },
  "rules": { "high_severity_count": 0, "passed": true }
}
```

---

## Getting Help

```bash
# Submission help
python scripts/submit_integrated_batch.py --help

# Cleanup help
python scripts/slurm/slurm_cleanup_cache.py --help

# Full documentation
cat CLUSTER_USAGE_GUIDE.md
```

---

**Pro Tips:**

1. ✅ **Always dry-run first** - See what will happen
2. ✅ **Monitor storage** - Check status every hour for large batches
3. ✅ **Start small** - Test with 5-10 instances first
4. ✅ **Cleanup between batches** - Don't let cache grow unbounded
5. ✅ **Use module control** - Disable what you don't need for faster results

---

**Need more details?** See `CLUSTER_USAGE_GUIDE.md`
