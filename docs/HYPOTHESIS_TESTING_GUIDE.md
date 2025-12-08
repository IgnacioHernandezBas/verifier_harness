# Hypothesis Fuzzing Tests with Singularity Containers

Complete guide for running Hypothesis-based fuzzing tests in SWE-bench containers.

## The Challenge

SWE-bench containers are minimal base environments that don't include:
- pytest
- hypothesis  
- coverage
- The actual package being tested (scikit-learn, etc.)

## The Solution: Three-Layer Approach

### Layer 1: Base Container (Cached, Read-Only)
- Downloaded once from Docker Hub
- Shared across all jobs
- Never modified
- Location: `/fs/nexus-scratch/ihbas/.cache/swebench_singularity/`

### Layer 2: Package Installation (Per-Job, Persistent)
- Install the repository package (e.g., scikit-learn)
- Install test dependencies (pytest, hypothesis)
- Location: `/fs/nexus-scratch/ihbas/.local/pip_packages/`
- Reused across multiple test runs

### Layer 3: Writable Overlay (Per-Execution, Temporary)
- Using `--writable-tmpfs` flag
- Allows temporary modifications
- Discarded after each run

## Workflow

### Step 1: Build Base Container (One-Time)
```python
from swebench_singularity import Config, SingularityBuilder

config = Config()
# ... configure paths ...
config.set("docker.image_patterns", [
    "swebench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest",
])

builder = SingularityBuilder(config)
result = builder.build_instance(instance_id)
container_path = result.sif_path
```

### Step 2: Install Test Dependencies (One-Time Per Instance)
```python
from install_test_deps import install_test_dependencies

# Install pytest, hypothesis, coverage
result = install_test_dependencies(
    str(container_path),
    repo_path
)

# Dependencies installed to: /fs/nexus-scratch/ihbas/.local/pip_packages/
```

### Step 3: Install Package from Repository
```python
import subprocess

pip_base = "/fs/nexus-scratch/ihbas/.local/pip_packages"

install_cmd = [
    "singularity", "exec",
    "--writable-tmpfs",
    "--bind", f"{repo_path}:/workspace",
    "--bind", f"{pip_base}:/pip_install_base",
    "--pwd", "/workspace",
    "--env", "PYTHONUSERBASE=/pip_install_base",
    str(container_path),
    "pip", "install", "--user", "-e", "."
]

subprocess.run(install_cmd, check=True)
```

### Step 4: Generate and Run Hypothesis Tests
```python
from scripts.run_hypothesis_tests import generate_and_run_hypothesis_tests

result = generate_and_run_hypothesis_tests(
    container_path=str(container_path),
    repo_path=repo_path,
    patch_analysis=patch_analysis,
    patched_code=patched_code,
    timeout=300
)

if result["success"]:
    print(f"✓ {result['test_count']} Hypothesis tests passed!")
    print(f"Coverage: {result['coverage']}")
else:
    print(f"✗ Tests failed!")
```

## Complete Example (Notebook Cell)

```python
# Stage 4a: Install Test Dependencies (do this once)
print("📦 Installing test dependencies...")

from install_test_deps import install_test_dependencies

deps_result = install_test_dependencies(
    str(CONTAINER_IMAGE_PATH),
    Path(repo_path)
)

if deps_result["success"]:
    print("✓ pytest, hypothesis, coverage installed")
else:
    print("⚠️ Warning:", deps_result["stderr"])

# Stage 4b: Install Package
print("📦 Installing package from repository...")

pip_base = Path("/fs/nexus-scratch/ihbas/.local/pip_packages")

install_pkg_cmd = [
    "singularity", "exec",
    "--writable-tmpfs",
    "--bind", f"{repo_path}:/workspace",
    "--bind", f"{pip_base}:/pip_install_base",
    "--pwd", "/workspace",
    "--env", "PYTHONUSERBASE=/pip_install_base",
    "--env", "PYTHONPATH=/workspace",
    str(CONTAINER_IMAGE_PATH),
    "pip", "install", "--user", "-e", "."
]

pkg_result = subprocess.run(install_pkg_cmd, capture_output=True, text=True)

if pkg_result.returncode == 0:
    print("✓ Package installed")
else:
    print("⚠️ Package install had issues")

# Stage 8-9: Generate and Run Hypothesis Tests
if patch_analysis and patch_analysis.changed_functions:
    print("🧬 Generating and running Hypothesis tests...")
    
    from scripts.run_hypothesis_tests import generate_and_run_hypothesis_tests
    
    test_result = generate_and_run_hypothesis_tests(
        container_path=str(CONTAINER_IMAGE_PATH),
        repo_path=Path(repo_path),
        patch_analysis=patch_analysis,
        patched_code=patched_code,
        timeout=300
    )
    
    if test_result["success"]:
        print(f"✓ {test_result['test_count']} Hypothesis tests PASSED")
    else:
        print(f"❌ Hypothesis tests FAILED")
        print(test_result["stderr"][-1000:])
```

## Key Concepts

### --writable-tmpfs
- Makes the container filesystem temporarily writable
- Changes are discarded when container exits
- Allows pip installs without modifying base .sif file

### --bind with Persistent Directory
- Mount a host directory into the container
- `--bind /host/path:/container/path`
- Changes persist on host filesystem
- Used for pip install location

### PYTHONUSERBASE
- Tells pip where to install packages
- Set to the bind-mounted directory
- Makes installed packages available across runs

## Directory Structure

```
/fs/nexus-scratch/ihbas/
├── .cache/swebench_singularity/          # Base containers (read-only)
│   └── scikit-learn/
│       └── scikit-learn__...-10297.sif
├── .local/pip_packages/                   # Test deps (persistent)
│   ├── bin/pytest
│   ├── lib/python3.X/site-packages/
│   │   ├── hypothesis/
│   │   ├── pytest/
│   │   ├── coverage/
│   │   └── scikit_learn/  (if installed with --user)
└── verifier_harness/
    └── repos_temp/                        # Repository code
        └── scikit-learn__scikit-learn/
```

## Advantages of This Approach

1. **Base containers never modified** - Can be shared/cached safely
2. **Test deps installed once** - Reused across multiple test runs
3. **No container rebuilding** - Fast iterations
4. **Parallel-safe** - Multiple jobs can use same base container
5. **Clean separation** - Base, deps, and code are separate layers

## SLURM Integration

The batch scripts already use this approach:

```bash
# In slurm_batch_analyze.sh
export APPTAINER_DOCKER_USERNAME="..."
export APPTAINER_DOCKER_PASSWORD="..."

# Worker script will:
# 1. Use cached container
# 2. Install deps to shared location
# 3. Install package
# 4. Run Hypothesis tests
# 5. Collect results
```

## Troubleshooting

**Tests can't find package?**
→ Make sure `PYTHONPATH=/workspace` is set and package is installed

**Hypothesis not found?**
→ Re-run `install_test_dependencies()`

**Permission denied?**
→ Use `--writable-tmpfs` flag

**Tests timeout?**
→ Increase timeout parameter in `generate_and_run_hypothesis_tests()`

## Performance Tips

1. **Install deps once per instance** - Not per test run
2. **Reuse pip_packages directory** - Shared across jobs
3. **Keep base containers cached** - Don't force rebuild
4. **Use job arrays** - Install deps in parallel for multiple instances
