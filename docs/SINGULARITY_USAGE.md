# Singularity-Based SWE-bench Testing

This guide describes how to use the Singularity-based test patch system for SWE-bench evaluation on the Nexus cluster.

## Overview

Due to rootless podman requiring subuid/subgid configuration (which requires admin privileges), we've switched to using Singularity/Apptainer, which is already installed and working on the Nexus cluster.

## Files

- **`verifier/dynamic_analyzers/test_patch_singularity.py`** - Core evaluation module using Singularity
- **`verifier/dynamic_analyzers/test_real_patch_singularity.py`** - Test script for real SWE-bench instances
- **`test_singularity_build.py`** - Simple script to build/verify the Singularity image

## Singularity Image

**Location:** `/scratch0/ihbas/.containers/singularity/verifier-swebench.sif`

**Size:** 168MB

**Contents:**
- Python 3.11.14
- pytest 9.0.0
- pytest-xdist 3.8.0
- hypothesis 6.147.0
- coverage 7.11.3
- git and build-essential

**Build command:**
```bash
python test_singularity_build.py
```

The image is cached, so subsequent runs won't rebuild unless you use `force_rebuild=True`.

## Usage

### 1. Test with a Real SWE-bench Instance

```bash
# Test the first available instance
python verifier/dynamic_analyzers/test_real_patch_singularity.py

# Test a specific instance
python verifier/dynamic_analyzers/test_real_patch_singularity.py \
    --instance-id "sympy__sympy-20590"

# Test from a specific repository
python verifier/dynamic_analyzers/test_real_patch_singularity.py \
    --repo "django/django"

# Force rebuild of Singularity image
python verifier/dynamic_analyzers/test_real_patch_singularity.py \
    --force-rebuild
```

### 2. Use in Python Code

```python
from verifier.dynamic_analyzers.test_patch_singularity import run_evaluation

predictions = [
    {
        "instance_id": "sympy__sympy-20590",
        "model_name_or_path": "gpt-4",
        "model_patch": "diff --git a/...\n...",
    }
]

results = run_evaluation(
    predictions=predictions,
    image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
    dataset_source="princeton-nlp/SWE-bench_Verified",
    hf_mode=True,
    split="test",
)

print(results)
```

### 3. Build or Rebuild Singularity Image

```python
from verifier.dynamic_analyzers.test_patch_singularity import build_singularity_image

# Build image (will skip if already exists)
image_path = build_singularity_image(
    image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
    python_version="3.11",
    force_rebuild=False,
)

# Force rebuild
image_path = build_singularity_image(
    image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
    python_version="3.11",
    force_rebuild=True,
)
```

### 4. Run Tests Directly in Singularity

```python
from pathlib import Path
from verifier.dynamic_analyzers.test_patch_singularity import run_tests_in_singularity

result = run_tests_in_singularity(
    repo_path=Path("/path/to/repo"),
    tests=["tests/test_foo.py::test_bar"],
    image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
)

print(f"Return code: {result['returncode']}")
print(f"Stdout: {result['stdout']}")
print(f"Stderr: {result['stderr']}")
```

## Command-Line Options

### test_real_patch_singularity.py

```
--dataset DATASET         HuggingFace dataset name
                         (default: princeton-nlp/SWE-bench_Verified)

--split SPLIT            Dataset split (default: test)

--instance-id ID         Specific instance ID to test
                         (e.g., astropy__astropy-12907)

--repo REPO              Filter by repository
                         (e.g., astropy/astropy)

--limit N                Number of samples to test (default: 1)

--image-path PATH        Path to Singularity image
                         (default: /scratch0/ihbas/.containers/singularity/verifier-swebench.sif)

--force-rebuild          Force rebuild of Singularity image
```

## Advantages of Singularity vs Podman

1. **No UID/GID mapping issues** - Works without `/etc/subuid` and `/etc/subgid` configuration
2. **HPC-optimized** - Designed for shared computing environments
3. **Better filesystem support** - Works well with NFS and scratch filesystems
4. **Single file images** - `.sif` files are portable and easy to manage
5. **Already installed** - No need to request admin configuration changes

## Troubleshooting

### Image doesn't exist
```bash
python test_singularity_build.py
```

### Want to rebuild image with different Python version
```python
from verifier.dynamic_analyzers.test_patch_singularity import build_singularity_image

build_singularity_image(
    image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench-py39.sif",
    python_version="3.9",
    force_rebuild=True,
)
```

### Check if Singularity is working
```bash
singularity --version
singularity exec /scratch0/ihbas/.containers/singularity/verifier-swebench.sif python --version
```

### Manually run pytest in container
```bash
singularity exec \
    --cleanenv \
    --containall \
    --bind /path/to/repo:/workspace \
    --pwd /workspace \
    /scratch0/ihbas/.containers/singularity/verifier-swebench.sif \
    pytest -v tests/
```

## Performance Notes

- **First build:** ~5-10 minutes (downloads base image and installs packages)
- **Subsequent uses:** Instant (uses cached `.sif` file)
- **Container startup:** Very fast (<1 second)
- **Test execution:** Similar to native Python

## Storage Locations

- **Singularity images:** `/scratch0/ihbas/.containers/singularity/`
- **Cloned repos:** `PROJECT_ROOT/repos_temp/` (by default)
- **Temp files:** System `/tmp/` during builds

## Migration from Podman

If you have existing code using `test_patch.py`, simply change:

```python
# Old (Podman)
from verifier.dynamic_analyzers.test_patch import run_evaluation

# New (Singularity)
from verifier.dynamic_analyzers.test_patch_singularity import run_evaluation
```

And update the parameter name:
```python
# Old
run_evaluation(image_name="verifier-swebench:latest", ...)

# New
run_evaluation(image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif", ...)
```

## Additional Resources

- Singularity documentation: https://sylabs.io/docs/
- Apptainer documentation: https://apptainer.org/docs/
- SWE-bench: https://github.com/princeton-nlp/SWE-bench

---

**Last Updated:** 2025-11-11
**Status:** Production Ready
**Tested on:** Nexus Cluster with Apptainer 1.4.4-1.el8
