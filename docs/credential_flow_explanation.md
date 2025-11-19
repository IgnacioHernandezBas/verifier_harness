# Docker Hub Authentication Flow

## Question: How are credentials used?

When you set credentials in the notebook, they flow through the system like this:

## The Flow

### 1. Set Credentials in Notebook
```python
import os
os.environ["SINGULARITY_DOCKER_USERNAME"] = "your_username"
os.environ["SINGULARITY_DOCKER_PASSWORD"] = "your_password"
```

These are now in your Python process's environment variables.

### 2. Notebook Calls Builder
```python
build_result = builder.build_instance(instance_id=instance_id)
```

### 3. Builder Checks Credentials
Inside `SingularityBuilder.build_instance()` → `build_from_docker()`:

```python
# Line 454 in singularity_builder.py
self._setup_docker_auth_env()
```

This method checks:
```python
# Lines 166-168
if "SINGULARITY_DOCKER_USERNAME" in os.environ and "SINGULARITY_DOCKER_PASSWORD" in os.environ:
    logger.debug("Singularity Docker credentials already set in environment")
    return
```

If they're already set (which they are!), it just returns.

### 4. Builder Runs Singularity Command
```python
# Lines 475-481 in singularity_builder.py
result = subprocess.run(
    cmd,  # ["singularity", "build", "--fakeroot", "output.sif", "docker://image"]
    capture_output=True,
    text=True,
    timeout=timeout,
    env=os.environ.copy(),  # ← HERE! Passes all environment variables
)
```

**Key line**: `env=os.environ.copy()`

This passes ALL environment variables (including your credentials) to the subprocess.

### 5. Singularity Uses Credentials
The `singularity build` command automatically looks for these environment variables:
- `SINGULARITY_DOCKER_USERNAME`
- `SINGULARITY_DOCKER_PASSWORD`

When Singularity needs to pull from Docker Hub, it reads these variables and uses them for authentication.

## Visual Flow

```
Notebook Cell
│
│ os.environ["SINGULARITY_DOCKER_USERNAME"] = "user"
│ os.environ["SINGULARITY_DOCKER_PASSWORD"] = "pass"
│
▼
Python Process Environment
│ SINGULARITY_DOCKER_USERNAME=user
│ SINGULARITY_DOCKER_PASSWORD=pass
│
▼
builder.build_instance(...)
│
├─► _setup_docker_auth_env()    [checks credentials exist ✓]
│
└─► subprocess.run(
       ["singularity", "build", ...],
       env=os.environ.copy()      [copies all env vars including credentials]
    )
    │
    ▼
    Singularity Process
    │ SINGULARITY_DOCKER_USERNAME=user
    │ SINGULARITY_DOCKER_PASSWORD=pass
    │
    └─► Pulls from Docker Hub using these credentials
```

## Code References

1. **Setting credentials**: Notebook auth-setup cell
2. **Checking credentials**: `swebench_singularity/singularity_builder.py:159-182` (_setup_docker_auth_env)
3. **Using credentials**: `swebench_singularity/singularity_builder.py:475-481` (subprocess.run with env=os.environ.copy())
4. **Singularity reads them**: Automatic - Singularity CLI reads these env vars when pulling Docker images

## Why This Works

Environment variables are inherited by child processes. When you:
1. Set `os.environ["VAR"] = "value"` in Python
2. Call `subprocess.run(..., env=os.environ.copy())`
3. The subprocess gets a copy of all environment variables
4. Singularity (the subprocess) can read them

## Testing It

You can verify credentials are being passed:

```python
import subprocess
import os

# Set credentials
os.environ["SINGULARITY_DOCKER_USERNAME"] = "myuser"

# Check they're in environment
print("In Python:", os.environ.get("SINGULARITY_DOCKER_USERNAME"))

# Check they're passed to subprocess
result = subprocess.run(
    ["bash", "-c", "echo $SINGULARITY_DOCKER_USERNAME"],
    capture_output=True,
    text=True,
    env=os.environ.copy()
)
print("In subprocess:", result.stdout.strip())
```

Output:
```
In Python: myuser
In subprocess: myuser
```

This proves the variable is passed to the subprocess, just like it's passed to singularity!
