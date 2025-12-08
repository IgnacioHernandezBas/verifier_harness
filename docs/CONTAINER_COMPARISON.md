# Container Runtime Comparison: Podman vs Singularity

This document compares Podman and Singularity for running SWE-bench tests on the Nexus cluster.

## Summary

| Feature | Podman | Singularity/Apptainer |
|---------|--------|----------------------|
| **Status on Nexus** | ❌ Blocked (no subuid/subgid) | ✅ Working |
| **Installation** | Available but unconfigured | Installed and ready |
| **Admin Required** | Yes (for subuid/subgid) | No |
| **Image Format** | OCI/Docker | SIF (single file) |
| **Image Size** | Similar (~168MB) | 168MB |
| **Build Time (first)** | ~5-10 min | ~5-10 min |
| **Subsequent Use** | Fast (cached) | Fast (cached) |
| **HPC Optimized** | No | Yes |
| **NFS/Scratch Support** | Can have issues | Excellent |

## The Problem with Podman

### Error Message
```
cannot find UID/GID for user ihbas: no subuid ranges found for user "ihbas" in /etc/subuid
```

### Root Cause
Rootless podman requires subordinate UID/GID ranges to be configured in:
- `/etc/subuid`
- `/etc/subgid`

These files require root access to configure.

### What Would Be Needed
A system administrator would need to run:
```bash
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 ihbas
# OR
echo "ihbas:100000:65536" | sudo tee -a /etc/subuid
echo "ihbas:100000:65536" | sudo tee -a /etc/subgid
```

Then you would run:
```bash
podman system migrate
```

## Why Singularity is Better for HPC

### 1. No Privileged Configuration Required
Singularity was designed for HPC environments where users don't have root access.

### 2. Single-File Images
- `.sif` files are immutable and portable
- Easy to share and version control
- No complex storage driver configuration needed

### 3. Native HPC Integration
- Works seamlessly with shared filesystems (NFS, Lustre, etc.)
- Integrates with job schedulers (SLURM, PBS, etc.)
- Respects filesystem quotas

### 4. Security Model
- Doesn't require daemon processes
- User inside container = user outside container (by default)
- No privilege escalation concerns

### 5. Performance
- Minimal overhead
- Direct I/O to bound filesystems
- Efficient image caching

## Implementation Differences

### File Structure

**Podman:**
```
/scratch0/ihbas/.containers/
├── storage/
│   ├── overlay/
│   ├── overlay-containers/
│   ├── overlay-images/
│   ├── overlay-layers/
│   └── db.sql
└── tmp/
```

**Singularity:**
```
/scratch0/ihbas/.containers/singularity/
└── verifier-swebench.sif  (168MB single file)
```

### Build Command

**Podman:**
```bash
podman --root /scratch0/ihbas/.containers/storage \
       --runroot /scratch0/ihbas/.containers/tmp \
       --storage-driver overlay \
       build -t verifier-swebench:latest .
```

**Singularity:**
```bash
singularity build verifier-swebench.sif verifier-swebench.def
```

### Run Command

**Podman:**
```bash
podman --root /scratch0/ihbas/.containers/storage \
       --runroot /scratch0/ihbas/.containers/tmp \
       --storage-driver overlay \
       run --rm -v /path:/workspace:Z image pytest
```

**Singularity:**
```bash
singularity exec \
    --cleanenv \
    --containall \
    --bind /path:/workspace \
    --pwd /workspace \
    image.sif \
    pytest
```

## API Comparison

### Podman Version
```python
from verifier.dynamic_analyzers.test_patch import run_evaluation

results = run_evaluation(
    predictions=predictions,
    image_name="verifier-swebench:latest",
    dataset_source="princeton-nlp/SWE-bench_Verified",
)
```

### Singularity Version
```python
from verifier.dynamic_analyzers.test_patch_singularity import run_evaluation

results = run_evaluation(
    predictions=predictions,
    image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
    dataset_source="princeton-nlp/SWE-bench_Verified",
)
```

The API is nearly identical - only the image specification differs!

## Migration Path

### If Podman Gets Fixed
If the system administrators configure subuid/subgid, you can use either runtime:

1. **Keep using Singularity** (recommended for HPC)
2. **Switch back to Podman** (if you prefer Docker-style workflow)
3. **Use both** (for maximum flexibility)

### Converting Between Formats
```bash
# Podman image → Singularity
podman save image:tag -o image.tar
singularity build image.sif docker-archive://image.tar

# Singularity → Podman
# (Not typically needed, but possible via Docker registry)
```

## Recommendation

**Use Singularity for production** on the Nexus cluster because:
1. ✅ Works right now without admin intervention
2. ✅ Better suited for HPC environments
3. ✅ Simpler storage management (single .sif file)
4. ✅ More reliable on shared filesystems
5. ✅ Standard in HPC community

**Keep Podman code** for:
- Development on local machines
- CI/CD pipelines
- Environments where Docker/Podman is standard

## Files Created

### Podman Version (Original)
- `verifier/dynamic_analyzers/test_patch.py`
- `verifier/dynamic_analyzers/test_real_patch.py`

### Singularity Version (New)
- `verifier/dynamic_analyzers/test_patch_singularity.py` ✅
- `verifier/dynamic_analyzers/test_real_patch_singularity.py` ✅
- `test_singularity_build.py` ✅

### Documentation
- `PODMAN_SETUP_GUIDE.md` (reference for podman issues)
- `SINGULARITY_USAGE.md` ✅ (primary guide)
- `CONTAINER_COMPARISON.md` ✅ (this file)

## Testing Status

### Singularity ✅
- [x] Image builds successfully
- [x] Python 3.11.14 works
- [x] pytest 9.0.0 works
- [x] Can mount directories
- [x] Can run tests
- [ ] Full SWE-bench evaluation (pending)

### Podman ❌
- [x] Installed on system
- [x] Configuration file created
- [ ] Blocked by subuid/subgid issue
- [ ] Requires admin intervention

## Next Steps

1. ✅ Use Singularity for all testing
2. ✅ Document the setup
3. ⏳ Run full SWE-bench evaluations
4. 📋 (Optional) Request admin to configure podman if needed for other tools

---

**Conclusion:** Singularity is the correct choice for the Nexus HPC cluster.
