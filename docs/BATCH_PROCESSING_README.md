# SWE-bench HPC Batch Processing Guide

Complete guide for running SWE-bench fuzzing analysis on HPC clusters using SLURM.

## Overview

This system provides two modes:
1. **Build Mode**: Pre-build containers for multiple instances (parallel, network-intensive)
2. **Analyze Mode**: Complete fuzzing pipeline per instance (CPU/memory intensive)

## Quick Start

### 1. Interactive Testing (Single Instance)

Use the Jupyter notebook for development and testing:
```bash
jupyter notebook fuzzing_pipeline_hpc_FIXED.ipynb
```

### 2. Batch Processing (Multiple Instances)

#### Option A: Two-Phase Approach (Recommended)

**Phase 1: Build all containers first**
```bash
# Build containers for 20 scikit-learn instances, max 10 parallel
./scripts/submit_batch.py --repo "scikit-learn/scikit-learn" --limit 20 --mode build --max-parallel 10
```

**Phase 2: Run analysis using cached containers**
```bash
# Analyze using pre-built containers, max 5 parallel (more CPU intensive)
./scripts/submit_batch.py --repo "scikit-learn/scikit-learn" --limit 20 --mode analyze --max-parallel 5
```

#### Option B: All-in-One (Single Phase)

```bash
# Build + analyze in one go (slower initial run, but simpler)
./scripts/submit_batch.py --repo "scikit-learn/scikit-learn" --limit 10 --mode analyze --max-parallel 3
```

## Files Created

```
verifier_harness/
├── scripts/slurm/slurm_batch_build_containers.sh  # SLURM script for container building
├── slurm_batch_analyze.sh           # SLURM script for full analysis
├── scripts/slurm/slurm_worker_build.py            # Python worker: build one container
├── scripts/slurm/slurm_worker_analyze.py          # Python worker: analyze one instance
├── scripts/submit_batch.py                  # Helper to submit jobs
├── instance_ids.txt                 # Auto-generated list of instances
├── logs/                            # Job logs (build_*, analyze_*)
├── results/                         # JSON results per instance
└── fuzzing_pipeline_hpc_FIXED.ipynb # Interactive notebook
```

## Usage Examples

### Example 1: Test on 5 pytest instances
```bash
./scripts/submit_batch.py --repo "pytest-dev/pytest" --limit 5 --mode analyze --max-parallel 2
```

### Example 2: Process entire test set (no filter)
```bash
./scripts/submit_batch.py --limit 100 --mode build --max-parallel 20
# Wait for builds to complete, then:
./scripts/submit_batch.py --limit 100 --mode analyze --max-parallel 10
```

### Example 3: Dry run (see what would happen)
```bash
./scripts/submit_batch.py --repo "django/django" --limit 10 --dry-run
```

## Monitoring Jobs

```bash
# View all your jobs
squeue -u $USER

# View specific job array
squeue -j <JOB_ID>

# Watch logs in real-time
tail -f logs/build_*.out
tail -f logs/analyze_*.out

# Check completed jobs
sacct -j <JOB_ID> --format=JobID,JobName,State,ExitCode,Elapsed

# View results
ls -lh results/
cat results/scikit-learn__scikit-learn-10297.json
```

## Resource Requirements

### Build Jobs (Container Download)
- **Time**: 1-2 hours (per container, first time only)
- **Memory**: 8 GB
- **CPU**: 2 cores
- **Network**: Heavy (1-2 GB download per container)
- **Storage**: ~1.2 GB per container (cached)

### Analysis Jobs (Full Pipeline)
- **Time**: 2-4 hours (per instance)
- **Memory**: 16 GB
- **CPU**: 4 cores
- **Disk I/O**: Moderate
- **Dependencies**: Pre-built container (or builds on demand)

## Optimizations

### 1. Pre-build Containers
Build all containers first using many parallel jobs (network-bound):
```bash
./scripts/submit_batch.py --limit 50 --mode build --max-parallel 20
```
Then analyze with fewer parallel jobs (CPU-bound):
```bash
./scripts/submit_batch.py --limit 50 --mode analyze --max-parallel 5
```

### 2. Shared Cache
All jobs share the container cache at:
```
/fs/nexus-scratch/ihbas/.cache/swebench_singularity/
```
Once a container is built, all subsequent jobs reuse it (< 1 second).

### 3. Adjust Parallelism
- **Build phase**: High parallelism OK (network-bound, little CPU)
- **Analysis phase**: Lower parallelism (CPU/memory intensive)

## Troubleshooting

### Job Failed with Timeout
Increase timeout in the SLURM script:
```bash
#SBATCH --time=06:00:00  # 6 hours instead of 2
```

### Out of Memory
Increase memory allocation:
```bash
#SBATCH --mem=32G  # 32 GB instead of 16
```

### Container Build Timeout
Edit `scripts/slurm/slurm_worker_build.py` and increase:
```python
config.set("singularity.build_timeout", 7200)  # 2 hours
```

### Authentication Errors
The SWE-bench images are PUBLIC - no authentication needed!
If you see auth errors, check the image pattern is correct in the script.

## Performance Tips

1. **Burst Build Phase**: Submit many build jobs at once (they're I/O bound)
2. **Staged Analysis**: After containers are cached, run analysis in batches
3. **Monitor Storage**: Each container ~1.2 GB, plan accordingly
4. **Use Job Dependencies**: Build jobs → analyze jobs (via `sbatch --dependency`)

## Advanced: Job Dependencies

Build first, then auto-start analysis when builds complete:
```bash
# Submit build job
BUILD_JOB=$(sbatch --parsable --array=1-10 scripts/slurm/slurm_batch_build_containers.sh)

# Submit analysis job that waits for builds
sbatch --dependency=afterok:$BUILD_JOB --array=1-10 slurm_batch_analyze.sh
```

## Results Format

Each instance produces a JSON file with:
```json
{
  "instance_id": "scikit-learn__scikit-learn-10297",
  "success": true,
  "sqi_score": 0.6154,
  "verdict": "ACCEPT",
  "container_from_cache": true,
  "duration_seconds": 450.2,
  "error": null
}
```

## Aggregate Results

```bash
# Count successes
grep -l '"success": true' results/*.json | wc -l

# Find failures
grep -l '"success": false' results/*.json

# Extract verdicts
jq -r '.verdict' results/*.json | sort | uniq -c
```

## Support

For issues:
1. Check logs in `logs/` directory
2. Verify container cache is accessible
3. Test single instance in notebook first
4. Check SLURM resource limits: `sinfo`, `slimits`
