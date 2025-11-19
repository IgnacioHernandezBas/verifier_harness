# Fuzzing Pipeline Notebooks Comparison

This document compares the original fuzzing pipeline notebook with the new HPC-optimized version.

## Notebooks Overview

### 1. `fuzzing_pipeline_analysis_clean.ipynb` (Original)
- Uses **static Singularity container** (single pre-built image)
- Hardcoded image path: `/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif`
- Manual container building required
- Limited to Python 3.11
- Same container for all SWE-bench instances

### 2. `fuzzing_pipeline_hpc_dynamic.ipynb` (New - HPC Optimized)
- Uses **dynamic container building** per SWE-bench instance
- Automatic Docker image resolution from multiple registries
- Intelligent caching system
- Instance-specific Python versions and dependencies
- HPC cluster optimized (no Docker daemon required)

## Key Differences

### Container Building

**Old Approach:**
```python
CONTAINER_IMAGE_PATH = "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif"
PYTHON_VERSION = "3.11"

image_path = build_singularity_image(
    CONTAINER_IMAGE_PATH,
    PYTHON_VERSION,
    force_rebuild=False
)
```

**New Approach:**
```python
# Configuration
config = Config()
builder = SingularityBuilder(config)

# Build instance-specific container
build_result = builder.build_instance(
    instance_id=instance_id,
    force_rebuild=False
)
CONTAINER_IMAGE_PATH = build_result.sif_path
```

### Docker Image Resolution

**Old:** Manual image specification
**New:** Automatic resolution from multiple sources:
- `aorwall/swe-bench-{repo}:{instance_id}`
- `swebench/{repo}:{instance_id}`
- `ghcr.io/swe-bench/{repo}:{instance_id}`

### Caching

**Old:** Single shared container
**New:** Per-instance caching with organization by repository:
```
~/.cache/swebench_singularity/
├── scikit-learn/
│   ├── scikit-learn__scikit-learn-10297.sif
│   └── scikit-learn__scikit-learn-10298.sif
├── pytest/
│   └── pytest-dev__pytest-5413.sif
└── ...
```

### Authentication

**Old:** Requires Docker daemon for authentication
**New:** Multiple authentication methods:
1. Singularity-native auth (SINGULARITY_DOCKER_USERNAME/PASSWORD)
2. Docker daemon (if available)
3. Docker config file (~/.docker/config.json)

## Feature Comparison Matrix

| Feature | Original | HPC Dynamic |
|---------|----------|-------------|
| Container per instance | ❌ | ✅ |
| Automatic Docker resolution | ❌ | ✅ |
| Intelligent caching | ❌ | ✅ |
| Works without Docker daemon | ⚠️ Limited | ✅ |
| Instance-specific Python versions | ❌ | ✅ |
| Retry logic | ❌ | ✅ (3 retries) |
| Build timeouts | ❌ | ✅ (30 min) |
| Cache management | ❌ | ✅ |
| Authentication verification | ❌ | ✅ |
| HPC cluster optimized | ⚠️ Partial | ✅ |

## When to Use Each

### Use Original (`fuzzing_pipeline_analysis_clean.ipynb`):
- Quick testing with a single instance
- All instances use same Python/deps
- Pre-built container already available
- Local development environment

### Use HPC Dynamic (`fuzzing_pipeline_hpc_dynamic.ipynb`):
- Running multiple different instances
- HPC cluster environment
- Need instance-specific containers
- Want automatic caching
- Production evaluations
- Batch processing

## Migration Guide

### Step 1: Install Dependencies
No additional dependencies required - uses existing codebase.

### Step 2: Configure Authentication
The new notebook includes an **Authentication Setup cell** that automatically checks for credentials.

**Option 1 - Set in Notebook (Recommended for Jupyter)**:
```python
import os
os.environ["SINGULARITY_DOCKER_USERNAME"] = "your_username"
os.environ["SINGULARITY_DOCKER_PASSWORD"] = "your_password"
```

**Option 2 - Set in Shell** (before starting Jupyter):
```bash
export SINGULARITY_DOCKER_USERNAME="your_dockerhub_username"
export SINGULARITY_DOCKER_PASSWORD="your_dockerhub_password"
```

**Option 3 - Use Docker Login**:
```bash
docker login
```

The notebook will automatically detect which method you used!

### Step 3: Update Configuration
The new notebook uses configuration that can be customized:
```python
config = Config()
config.set("singularity.cache_dir", "/your/cache/dir")
config.set("singularity.build_timeout", 1800)
```

### Step 4: Run
Just execute the cells - the system handles everything automatically!

## Performance Comparison

### Build Times (First Run)
- **Original**: 5-10 minutes (manual build)
- **HPC Dynamic**: 5-15 minutes (automatic, includes Docker pull)

### Build Times (Cached)
- **Original**: Instant (same container reused)
- **HPC Dynamic**: Instant (per-instance cache)

### Scalability
- **Original**: Limited (all instances share one container)
- **HPC Dynamic**: Excellent (isolated per instance, parallel builds possible)

## Architecture

### Original Architecture
```
Notebook → Static Container → All Instances
```

### HPC Dynamic Architecture
```
Notebook → Config → SingularityBuilder
                  ↓
              DockerResolver → Multiple Registries
                  ↓
              CacheManager → Organized Cache
                  ↓
          Instance-Specific Container → Test Execution
```

## Troubleshooting

### Issue: Authentication Errors
**Symptoms**: "UNAUTHORIZED" or "authentication required" errors during container build

**Solution**: The notebook now includes an authentication check cell. Run it to diagnose:
1. **If running in Jupyter**: Set credentials directly in the notebook:
   ```python
   import os
   os.environ["SINGULARITY_DOCKER_USERNAME"] = "your_username"
   os.environ["SINGULARITY_DOCKER_PASSWORD"] = "your_password"
   ```
   Then re-run the authentication check cell to verify.

2. **If shell variables don't work**: This is common in Jupyter. Shell environment variables set outside Jupyter may not be visible to the Python kernel. Always use Option 1 above for Jupyter notebooks.

3. **If Docker login doesn't work**: The notebook will detect `~/.docker/config.json` automatically

### Issue: Build Timeout
**Solution**: Increase timeout: `config.set("singularity.build_timeout", 3600)`

### Issue: Cache Full
**Solution**: Configure cleanup: `config.set("singularity.cleanup_after_days", 7)`

## Future Enhancements

The new dynamic system enables:
1. **Parallel builds** for multiple instances
2. **SLURM integration** for HPC job submission
3. **Automatic cache cleanup** based on age/size
4. **Build metrics** and monitoring
5. **Custom image patterns** per repository

## Summary

The new HPC dynamic notebook provides:
- ✅ Better isolation (per-instance containers)
- ✅ Automatic image management
- ✅ HPC cluster optimization
- ✅ Intelligent caching
- ✅ Production-ready scaling

Perfect for running comprehensive SWE-bench evaluations on HPC clusters!
