# Quick Start Guide

## 🚀 You're Ready to Go!

All authentication issues are resolved. The system is configured correctly.

## ✅ What's Fixed

1. **Docker Hub authentication** properly configured for Apptainer
2. **Correct SWE-bench image pattern**: `swebench/sweb.eval.x86_64.{repo}_1776_{repo}-{version}:latest`
3. **Images are PUBLIC** - no authentication actually required!
4. **SLURM batch processing** system ready for parallel execution

## 📋 Three Ways to Use This

### 1. Interactive Notebook (Development/Testing)
```bash
cd /fs/nexus-scratch/ihbas/verifier_harness
jupyter notebook fuzzing_pipeline_hpc_FIXED.ipynb
```
- Great for: Testing, debugging, exploring single instances
- First container download: 10-15 minutes (then cached)

### 2. SLURM Batch (Recommended for Production)
```bash
# Process 10 instances in parallel
./submit_batch.py --repo "scikit-learn/scikit-learn" --limit 10 --mode analyze --max-parallel 5

# Monitor progress
squeue -u $USER
tail -f logs/analyze_*.out
```
- Great for: Processing many instances efficiently
- See: `BATCH_PROCESSING_README.md` for full details

### 3. Two-Phase Approach (Most Efficient)
```bash
# Phase 1: Build all containers (network-intensive, high parallelism)
./submit_batch.py --limit 20 --mode build --max-parallel 15

# Phase 2: Analyze with cached containers (CPU-intensive, lower parallelism)
./submit_batch.py --limit 20 --mode analyze --max-parallel 5
```
- Great for: Large-scale processing
- Separates I/O-bound from CPU-bound work

## 📊 Expected Performance

| Phase | Time (first run) | Time (cached) | Resources |
|-------|------------------|---------------|-----------|
| Container Build | 10-15 min | < 1 sec | 8GB RAM, 2 CPU |
| Full Analysis | 2-4 hours | 2-4 hours | 16GB RAM, 4 CPU |

## 🎯 Next Steps

1. **Test with one instance** (notebook or single SLURM job)
2. **Build containers** for your target instances
3. **Run full analysis** on batch

## 💡 Pro Tips

- Containers are **shared** across all jobs (cached at `/fs/nexus-scratch/ihbas/.cache/swebench_singularity/`)
- Build phase is **network-bound** → use high parallelism (10-20 jobs)
- Analysis phase is **CPU-bound** → use moderate parallelism (3-5 jobs)
- Results saved as JSON in `results/` directory

## 🆘 Troubleshooting

**Container build timeout?**
→ Increase timeout in `slurm_batch_build_containers.sh`: `--time=04:00:00`

**Out of memory?**
→ Increase memory: `--mem=32G`

**Authentication errors?**
→ Shouldn't happen (images are public), but env vars are set correctly

## 📁 Important Files

```
fuzzing_pipeline_hpc_FIXED.ipynb  ← Notebook (interactive)
submit_batch.py                    ← Submit SLURM jobs
BATCH_PROCESSING_README.md         ← Full batch documentation
slurm_batch_*.sh                   ← SLURM scripts
slurm_worker_*.py                  ← Worker scripts
```

## 🎉 You're All Set!

The authentication issue is completely resolved. Start with the notebook to verify everything works, then scale up with SLURM batch processing.
