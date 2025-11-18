# SWE-bench Singularity Runner

A dynamic container management system for running SWE-bench evaluations with Singularity containers. This system eliminates the need for static container definitions by dynamically fetching and converting Docker images for each SWE-bench instance.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Single Instance Execution](#single-instance-execution)
  - [Batch Execution](#batch-execution)
  - [Cache Management](#cache-management)
- [Integration with Existing Pipeline](#integration-with-existing-pipeline)
- [Docker Image Naming Convention](#docker-image-naming-convention)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)

## Overview

SWE-bench contains 12 different repositories, each with hundreds of instances at different commits with different dependencies. The traditional approach of using a single static Singularity definition file doesn't scale.

This system solves the problem by:

1. **Dynamic Docker Image Resolution**: Maps instance IDs to Docker image names
2. **Automatic Conversion**: Converts Docker images to Singularity `.sif` files
3. **Intelligent Caching**: Caches converted images to avoid rebuilding
4. **Parallel Execution**: Runs multiple instances in parallel
5. **Integration Ready**: Integrates with existing change-aware fuzzing pipeline

## Architecture

```
swebench_singularity/
├── config.py              # Configuration management
├── docker_resolver.py     # Resolve Docker image names from instance IDs
├── singularity_builder.py # Convert Docker to Singularity with caching
├── cache_manager.py       # Manage .sif file cache
├── instance_runner.py     # Execute tests in containers
└── utils.py              # Shared utilities

Scripts:
├── run_swebench_instance.py   # Run single instance
├── run_swebench_batch.py      # Run multiple instances in parallel
└── swebench_cache_manager.py  # Manage cache

Configuration:
└── config/swebench_config.yaml # Configuration settings
```

### Key Components

#### 1. Docker Image Resolver

Handles the mapping from SWE-bench instance IDs to Docker image names.

**Instance ID Format**: `<org>__<repo>-<version>`
- Example: `django__django-12345`, `pytest-dev__pytest-7490`

**Docker Image Patterns** (tried in order):
1. `aorwall/swe-bench-{repo}:{instance_id}`
2. `swebench/{repo}:{instance_id}`
3. `ghcr.io/swe-bench/{repo}:{instance_id}`

#### 2. Singularity Builder

Converts Docker images to Singularity `.sif` files with:
- Automatic retry logic with exponential backoff
- Build timeout management
- Fakeroot support for rootless building
- Integration with cache manager

#### 3. Cache Manager

Manages the `.sif` file cache:
- Organizes by repository (optional)
- Tracks size and age
- Automatic cleanup policies
- Integrity verification

#### 4. Instance Runner

Executes tests in Singularity containers:
- Prepares containers
- Runs pytest with coverage
- Integrates with existing evaluation pipeline
- Handles timeouts and errors

## Features

✅ **Dynamic Container Management**
- No need for static Singularity definition files
- Automatically fetches and converts Docker images
- Supports all SWE-bench repositories

✅ **Intelligent Caching**
- Caches converted `.sif` files
- Organized by repository
- Automatic size and age-based cleanup
- Cache integrity verification

✅ **Parallel Execution**
- Run multiple instances simultaneously
- Configurable worker count
- Progress tracking
- Fail-fast mode

✅ **Robust Error Handling**
- Automatic retries with exponential backoff
- Timeout management
- Detailed logging
- Graceful degradation

✅ **Integration Ready**
- Works with existing change-aware fuzzing
- Compatible with SWE-bench dataset format
- Supports custom predictions
- Detailed result tracking

## Installation

### Prerequisites

1. **Singularity**: Version 3.0 or higher
   ```bash
   singularity --version
   ```

2. **Python**: Version 3.8 or higher
   ```bash
   python --version
   ```

3. **Required Python packages**:
   ```bash
   pip install pyyaml
   ```

### Setup

1. The system is already integrated into the verifier harness. No additional installation needed.

2. Verify configuration:
   ```bash
   python -c "from swebench_singularity import Config; c = Config(); print(c)"
   ```

3. Check Singularity availability:
   ```bash
   python run_swebench_instance.py --instance_id "test" --build-only 2>&1 | grep -i singularity
   ```

## Configuration

The system is configured via `config/swebench_config.yaml`.

### Key Configuration Sections

#### Docker Settings
```yaml
docker:
  registry: "docker.io"
  image_patterns:
    - "aorwall/swe-bench-{repo}:{instance_id}"
    - "swebench/{repo}:{instance_id}"
  pull_timeout: 600
  max_retries: 3
  retry_delay: 5
```

#### Singularity Settings
```yaml
singularity:
  cache_dir: "/fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache"
  tmp_dir: "/fs/nexus-scratch/ihbas/.singularity_tmp"
  build_timeout: 1800
  use_fakeroot: true
  cleanup_after_days: 30
  max_cache_size_gb: 100
```

#### Execution Settings
```yaml
execution:
  test_timeout: 300
  pytest_workers: 4
  use_writable_tmpfs: true
  bind_paths:
    - "/fs/nexus-scratch/ihbas/.local:/home/user/.local"
```

#### Parallel Execution
```yaml
parallel:
  max_workers: 10
  chunk_size: 5
  fail_fast: false
```

### Override Configuration

You can override configuration via:

1. **Command-line arguments**:
   ```bash
   python run_swebench_instance.py \
       --instance_id "pytest-dev__pytest-7490" \
       --cache_dir "/custom/cache" \
       --timeout 600
   ```

2. **Environment variables**:
   ```bash
   export SINGULARITY_TMPDIR=/tmp/singularity
   python run_swebench_instance.py --instance_id "..."
   ```

3. **Custom config file**:
   ```bash
   python run_swebench_instance.py \
       --instance_id "..." \
       --config my_config.yaml
   ```

## Usage

### Single Instance Execution

#### Basic Usage

```bash
# Run a single instance
python run_swebench_instance.py --instance_id "django__django-12345"
```

#### With Custom Predictions

```bash
python run_swebench_instance.py \
    --instance_id "pytest-dev__pytest-7490" \
    --predictions_path "my_predictions.json"
```

#### Build Only (No Test Execution)

```bash
python run_swebench_instance.py \
    --instance_id "flask__flask-4992" \
    --build-only
```

#### Force Rebuild

```bash
python run_swebench_instance.py \
    --instance_id "requests__requests-3362" \
    --force-rebuild
```

#### Custom Timeout

```bash
python run_swebench_instance.py \
    --instance_id "sympy__sympy-20590" \
    --timeout 600
```

#### Verbose Logging

```bash
python run_swebench_instance.py \
    --instance_id "django__django-12345" \
    --verbose \
    --log-file run.log
```

### Batch Execution

#### Run Multiple Instances from File

```bash
# Create instance list file
cat > instances.txt << 'EOF'
django__django-12345
pytest-dev__pytest-7490
flask__flask-4992
EOF

# Run batch
python run_swebench_batch.py --instance_list instances.txt
```

#### Parallel Execution

```bash
# Run with 10 parallel workers
python run_swebench_batch.py \
    --instance_list instances.txt \
    --workers 10
```

#### From Predictions File

```bash
python run_swebench_batch.py \
    --predictions predictions.json \
    --output results.json
```

#### Filter by Repository

```bash
python run_swebench_batch.py \
    --instance_list instances.txt \
    --repo pytest \
    --output pytest_results.json
```

#### Limit Number of Instances

```bash
python run_swebench_batch.py \
    --instance_list instances.txt \
    --limit 10 \
    --skip 5
```

#### Resume from Previous Run

```bash
# First run (interrupted)
python run_swebench_batch.py \
    --instance_list instances.txt \
    --output results.json

# Resume
python run_swebench_batch.py \
    --instance_list instances.txt \
    --output results.json \
    --resume results.json
```

#### Fail-Fast Mode

```bash
python run_swebench_batch.py \
    --instance_list instances.txt \
    --fail-fast
```

#### Build Only (Pre-cache)

```bash
# Build all containers without running tests (good for pre-caching)
python run_swebench_batch.py \
    --instance_list instances.txt \
    --build-only \
    --workers 20
```

### Cache Management

#### View Cache Statistics

```bash
python swebench_cache_manager.py stats
```

Output:
```
============================================================
Singularity Cache Statistics
============================================================
Location: /fs/nexus-scratch/ihbas/.containers/singularity/swebench_cache
Total Entries: 45
Total Size: 12.34 GB
Oldest Entry: django__django-11000 (15.3 days)
Newest Entry: pytest-dev__pytest-7490 (0.5 days)
Largest Entry: sympy__sympy-20590 (456.7 MB)
============================================================
```

#### List Cached Instances

```bash
# List all
python swebench_cache_manager.py list

# Filter by repository
python swebench_cache_manager.py list --repo pytest

# Sort by size
python swebench_cache_manager.py list --sort size

# Sort by age
python swebench_cache_manager.py list --sort age
```

#### Clean Cache

```bash
# Remove entries older than 30 days
python swebench_cache_manager.py clean --days 30

# Clean to reduce size below 50 GB
python swebench_cache_manager.py clean --max-size 50

# Combine both
python swebench_cache_manager.py clean --days 30 --max-size 50

# Skip confirmation
python swebench_cache_manager.py clean --days 30 -y
```

#### Remove Specific Instance

```bash
python swebench_cache_manager.py remove --instance_id "django__django-12345"
```

#### Clear Entire Cache

```bash
python swebench_cache_manager.py clear
```

#### Verify Cache Integrity

```bash
python swebench_cache_manager.py verify
```

#### Generate Report

```bash
# Display report
python swebench_cache_manager.py report

# Save to file
python swebench_cache_manager.py report --output cache_report.txt
```

## Integration with Existing Pipeline

The new Singularity runner integrates seamlessly with the existing change-aware fuzzing pipeline.

### Integration Points

1. **Dataset Loading**: Uses existing `swebench_integration/dataset_loader.py`
2. **Patch Application**: Uses existing `swebench_integration/patch_loader.py`
3. **Fuzzing**: Can enable/disable via config:
   ```yaml
   integration:
     enable_fuzzing: true
     enable_static_analysis: true
   ```

### Example Integration

```python
from swebench_singularity import InstanceRunner, Config
from verifier.dynamic_analyzers.test_patch_singularity import run_evaluation

# Configure
config = Config()
config.set("integration.enable_fuzzing", True)

# Run instance with existing pipeline
runner = InstanceRunner(config)
result = runner.run_swebench_instance(
    instance_id="pytest-dev__pytest-7490",
    predictions_path="predictions.json"
)

# Result includes fuzzing analysis if enabled
print(f"Success: {result.success}")
print(f"Tests: {result.passed_tests}/{result.total_tests}")
```

## Docker Image Naming Convention

### SWE-bench Official Images

The official SWE-bench Docker images follow this convention:

**Format**: `aorwall/swe-bench-{repo}:{instance_id}`

**Examples**:
- `aorwall/swe-bench-pytest:pytest-dev__pytest-7490`
- `aorwall/swe-bench-django:django__django-12345`
- `aorwall/swe-bench-flask:flask__flask-4992`

### Repository Mapping

The system maps full repository names to short names:

| Full Name | Short Name | Docker Image |
|-----------|------------|--------------|
| `pytest-dev/pytest` | `pytest` | `aorwall/swe-bench-pytest` |
| `django/django` | `django` | `aorwall/swe-bench-django` |
| `pallets/flask` | `flask` | `aorwall/swe-bench-flask` |
| `psf/requests` | `requests` | `aorwall/swe-bench-requests` |
| `sympy/sympy` | `sympy` | `aorwall/swe-bench-sympy` |

### Custom Patterns

You can add custom patterns in `config/swebench_config.yaml`:

```yaml
docker:
  image_patterns:
    - "aorwall/swe-bench-{repo}:{instance_id}"
    - "my-registry/swebench/{repo}:{version}"
    - "ghcr.io/my-org/{repo}:{instance_id}"
```

## Troubleshooting

### Common Issues

#### 1. Singularity Not Found

**Error**: `Singularity command not found`

**Solution**:
```bash
# Check if Singularity is installed
which singularity

# If not, install Singularity
# https://sylabs.io/docs/
```

#### 2. Docker Image Not Found

**Error**: `No available Docker images found for {instance_id}`

**Solution**:
1. Check if the instance ID format is correct
2. Verify Docker registry is accessible
3. Try with `--no-check-docker-exists` to skip verification
4. Add custom image patterns in config

```bash
python run_swebench_instance.py \
    --instance_id "django__django-12345" \
    --verbose
```

#### 3. Build Timeout

**Error**: `Build timeout after 1800s`

**Solution**: Increase build timeout in config or via argument

```yaml
singularity:
  build_timeout: 3600  # 1 hour
```

#### 4. Permission Denied

**Error**: `Permission denied` or `FAKEROOT not enabled`

**Solution**:
1. Enable fakeroot in config:
   ```yaml
   singularity:
     use_fakeroot: true
   ```

2. Or configure Singularity for unprivileged builds:
   ```bash
   singularity config fakeroot --add $USER
   ```

#### 5. Cache Full

**Error**: `No space left on device`

**Solution**: Clean cache

```bash
# Clean old entries
python swebench_cache_manager.py clean --days 7

# Reduce cache size
python swebench_cache_manager.py clean --max-size 20
```

### Debug Mode

Enable debug logging for detailed information:

```bash
python run_swebench_instance.py \
    --instance_id "..." \
    --verbose \
    --log-file debug.log
```

## Performance

### Benchmarks

Based on typical usage on Nexus cluster:

| Operation | Time | Notes |
|-----------|------|-------|
| Docker → Singularity conversion | 5-15 min | First time only |
| Cache lookup | <1 second | Instant if cached |
| Test execution | 1-5 min | Depends on test suite |
| Batch processing (10 instances, 10 workers) | 10-20 min | With caching |

### Optimization Tips

1. **Pre-cache containers** before running tests:
   ```bash
   python run_swebench_batch.py --instance_list all_instances.txt --build-only --workers 20
   ```

2. **Use parallel execution** for batch processing:
   ```bash
   python run_swebench_batch.py --instance_list instances.txt --workers 10
   ```

3. **Organize cache by repository** for better management:
   ```yaml
   cache:
     organize_by_repo: true
   ```

4. **Set appropriate cleanup policies**:
   ```yaml
   singularity:
     cleanup_after_days: 7
     max_cache_size_gb: 50
   ```

5. **Use fast storage** for cache directory (SSD preferred)

### Expected Throughput

- **With caching**: 10-20 instances/hour (1 worker)
- **Parallel (10 workers)**: 100-200 instances/hour
- **Build-only**: 5-10 instances/hour (limited by Docker pull)

## Best Practices

1. **Always use caching** unless you have a specific reason not to
2. **Pre-build containers** for large batch jobs
3. **Use parallel execution** for better throughput
4. **Monitor cache size** and clean regularly
5. **Set appropriate timeouts** based on test complexity
6. **Use fail-fast mode** for debugging
7. **Enable logging** for production runs
8. **Save results** to JSON for analysis
9. **Verify cache integrity** periodically
10. **Use resume feature** for interrupted batch jobs

## Future Enhancements

Planned features:

- [ ] Integration with SLURM for HPC batch jobs
- [ ] Automatic cache warming from SWE-bench dataset
- [ ] Support for custom container registry authentication
- [ ] Distributed caching across cluster nodes
- [ ] Real-time progress dashboard
- [ ] Integration with existing verifier UI
- [ ] Automatic container updates when Docker images change
- [ ] Support for multi-stage builds
- [ ] Container image compression
- [ ] Advanced filtering and querying

## Support

For issues or questions:

1. Check this documentation
2. Enable verbose logging: `--verbose`
3. Check cache statistics: `python swebench_cache_manager.py stats`
4. Verify Singularity: `singularity --version`
5. Test with a known instance: `pytest-dev__pytest-7490`

## License

This code is part of the SWE-bench Verifier Harness project.

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
