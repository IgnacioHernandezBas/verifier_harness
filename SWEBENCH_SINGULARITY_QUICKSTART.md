# SWE-bench Singularity Runner - Quick Start Guide

Get started with the dynamic Singularity runner in 5 minutes!

## Prerequisites

✅ Singularity installed and available
✅ Python 3.8+
✅ Access to Docker registry (docker.io)

## Quick Start

### 1. Run Your First Instance

```bash
# Simple example - run a single pytest instance
python run_swebench_instance.py --instance_id "pytest-dev__pytest-7490"
```

**What happens:**
1. ✅ Resolves Docker image: `aorwall/swe-bench-pytest:pytest-dev__pytest-7490`
2. ✅ Converts to Singularity: `pytest-dev__pytest-7490.sif`
3. ✅ Caches the `.sif` file for future use
4. ✅ Runs tests in container
5. ✅ Reports results

**Expected output:**
```
INFO - Building container for pytest-dev__pytest-7490...
INFO - ✓ Container ready: /path/to/cache/pytest-dev__pytest-7490.sif (8m 23s)
INFO - Running SWE-bench Instance: pytest-dev__pytest-7490
INFO - ✓ SUCCESS
INFO - Tests Passed: 15/15
```

### 2. Run Multiple Instances in Parallel

```bash
# Create a list of instances
cat > instances.txt << 'EOF'
pytest-dev__pytest-7490
pytest-dev__pytest-5692
pytest-dev__pytest-5413
EOF

# Run in parallel with 3 workers
python run_swebench_batch.py \
    --instance_list instances.txt \
    --workers 3 \
    --output results.json
```

**What happens:**
1. ✅ Loads 3 instance IDs from file
2. ✅ Builds containers in parallel (3 at a time)
3. ✅ Runs tests for each instance
4. ✅ Saves results to `results.json`

### 3. View Cache Statistics

```bash
python swebench_cache_manager.py stats
```

**Output:**
```
============================================================
Singularity Cache Statistics
============================================================
Location: /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache
Total Entries: 3
Total Size: 1.23 GB
============================================================
```

## Common Use Cases

### Use Case 1: Test a Specific Instance with Your Patch

```bash
# Create a patch file
cat > my_fix.diff << 'EOF'
--- a/src/_pytest/logging.py
+++ b/src/_pytest/logging.py
@@ -100,7 +100,7 @@ def pytest_configure(config):
-    if config.option.debug:
+    if config.option.verbose:
         logger.setLevel(logging.DEBUG)
EOF

# Run with your patch
python run_swebench_instance.py \
    --instance_id "pytest-dev__pytest-7490" \
    --predictions_path my_fix.diff
```

### Use Case 2: Pre-build Containers for a Project

```bash
# Get all pytest instances
cat > pytest_instances.txt << 'EOF'
pytest-dev__pytest-7490
pytest-dev__pytest-5692
pytest-dev__pytest-5413
pytest-dev__pytest-4629
pytest-dev__pytest-7168
EOF

# Pre-build (don't run tests yet)
python run_swebench_batch.py \
    --instance_list pytest_instances.txt \
    --build-only \
    --workers 5
```

This caches all containers for future use!

### Use Case 3: Filter and Run Specific Repository

```bash
# Run only pytest instances from a mixed list
python run_swebench_batch.py \
    --instance_list all_instances.txt \
    --repo pytest \
    --workers 10
```

### Use Case 4: Resume Interrupted Batch

```bash
# First run (gets interrupted)
python run_swebench_batch.py \
    --instance_list instances.txt \
    --output results.json

# Resume from where it left off
python run_swebench_batch.py \
    --instance_list instances.txt \
    --output results.json \
    --resume results.json
```

### Use Case 5: Clean Old Cache

```bash
# Remove entries older than 7 days
python swebench_cache_manager.py clean --days 7 -y

# Keep cache under 20 GB
python swebench_cache_manager.py clean --max-size 20 -y
```

## Configuration

### Default Configuration

The system uses `config/swebench_config.yaml` by default. Key settings:

```yaml
# Cache location
singularity:
  cache_dir: "/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache"

# Parallel workers
parallel:
  max_workers: 10

# Execution timeout
execution:
  test_timeout: 300  # 5 minutes
```

### Override Configuration

```bash
# Custom cache directory
python run_swebench_instance.py \
    --instance_id "pytest-dev__pytest-7490" \
    --cache_dir "/my/cache/dir"

# Custom timeout
python run_swebench_instance.py \
    --instance_id "pytest-dev__pytest-7490" \
    --timeout 600

# More workers
python run_swebench_batch.py \
    --instance_list instances.txt \
    --workers 20
```

## Workflow Examples

### Example 1: Complete Evaluation Pipeline

```bash
#!/bin/bash

# 1. Get predictions from your model
# (Assume model_predictions.json exists)

# 2. Pre-build all required containers
python run_swebench_batch.py \
    --predictions model_predictions.json \
    --build-only \
    --workers 10

# 3. Run evaluations in parallel
python run_swebench_batch.py \
    --predictions model_predictions.json \
    --workers 10 \
    --output final_results.json

# 4. View statistics
python swebench_cache_manager.py stats

# 5. Clean cache
python swebench_cache_manager.py clean --days 30 -y

echo "Done! Results in final_results.json"
```

### Example 2: Development/Testing Workflow

```bash
#!/bin/bash

# Test a single instance first
python run_swebench_instance.py \
    --instance_id "pytest-dev__pytest-7490" \
    --verbose

# If successful, run a small batch
python run_swebench_batch.py \
    --instance_list pytest_test.txt \
    --limit 5 \
    --verbose

# Then run full batch
python run_swebench_batch.py \
    --instance_list pytest_all.txt \
    --workers 10
```

### Example 3: HPC Cluster Workflow

```bash
#!/bin/bash
#SBATCH --job-name=swebench-eval
#SBATCH --partition=cml-scavenger
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=20
#SBATCH --mem=64G

# Load environment
module load singularity

# Run batch evaluation
python run_swebench_batch.py \
    --predictions predictions.json \
    --workers $SLURM_CPUS_PER_TASK \
    --output results_${SLURM_JOB_ID}.json \
    --log-file logs/run_${SLURM_JOB_ID}.log

# Clean cache after completion
python swebench_cache_manager.py clean --days 7 -y
```

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| "Singularity not found" | Install Singularity or load module: `module load singularity` |
| "Docker image not found" | Check instance ID format, enable verbose: `--verbose` |
| "Build timeout" | Increase timeout: `--timeout 3600` or in config |
| "Permission denied" | Use fakeroot (enabled by default in config) |
| "No space left" | Clean cache: `python swebench_cache_manager.py clean --days 7` |
| "Instance failed" | Check logs: `--verbose --log-file debug.log` |

## Performance Tips

1. **Pre-build containers** before running tests:
   ```bash
   python run_swebench_batch.py --instance_list all.txt --build-only --workers 20
   ```

2. **Use parallel execution** for batches:
   ```bash
   python run_swebench_batch.py --instance_list all.txt --workers 10
   ```

3. **Monitor cache size**:
   ```bash
   python swebench_cache_manager.py stats
   ```

4. **Clean regularly**:
   ```bash
   # Add to crontab for weekly cleanup
   0 0 * * 0 python /path/to/swebench_cache_manager.py clean --days 30 -y
   ```

## Next Steps

1. **Read full documentation**: `Documentation/SWEBENCH_SINGULARITY_RUNNER.md`
2. **Explore configuration**: `config/swebench_config.yaml`
3. **Try different repositories**: django, flask, sympy, etc.
4. **Integrate with your pipeline**: See integration examples
5. **Scale up**: Use SLURM for large-scale evaluation

## Example: Complete Run

Let's run a complete example:

```bash
# 1. Create test instance list
cat > test_instances.txt << 'EOF'
pytest-dev__pytest-7490
flask__flask-4992
requests__requests-3362
EOF

# 2. Build containers
echo "Building containers..."
python run_swebench_batch.py \
    --instance_list test_instances.txt \
    --build-only \
    --workers 3

# 3. View cache
echo "Cache status:"
python swebench_cache_manager.py stats

# 4. List cached instances
echo "Cached instances:"
python swebench_cache_manager.py list

# 5. Run tests
echo "Running tests..."
python run_swebench_batch.py \
    --instance_list test_instances.txt \
    --workers 3 \
    --output test_results.json

# 6. View results
echo "Results:"
python -m json.tool test_results.json | head -50

# 7. Clean up (optional)
# python swebench_cache_manager.py clear -y
```

## Support Commands

```bash
# Get help
python run_swebench_instance.py --help
python run_swebench_batch.py --help
python swebench_cache_manager.py --help

# Check version
python -c "from swebench_singularity import __version__; print(__version__)"

# Verify installation
python -c "from swebench_singularity import Config; print('OK')"

# Test Singularity
singularity --version
```

---

**You're ready to go!** 🚀

Start with a single instance, then scale up to batch processing.

For detailed documentation, see: `Documentation/SWEBENCH_SINGULARITY_RUNNER.md`
