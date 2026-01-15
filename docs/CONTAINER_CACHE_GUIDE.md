# Container Cache Management Guide

## Overview

Your Singularity containers are cached on the shared NFS filesystem, making them accessible from **any cluster node** without rebuilding.

## Cache Location

```bash
/fs/nexus-scratch/ihbas/.cache/swebench_singularity/
```

**Filesystem**: NFS mount → `192.168.43.141:/nexus/scratch`

## Benefits of Shared Cache

✅ **Node-Independent**: Built once, use from any compute node
✅ **Rate Limit Protection**: Avoids repeated Docker Hub pulls
✅ **Faster Startup**: No rebuild time, instant container reuse
✅ **Disk Efficient**: 23GB shared cache vs. duplicates per node

## Checking Your Cache

### List All Containers

```bash
# List all cached containers
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif"

# Count containers
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" | wc -l

# Show cache size
du -sh /fs/nexus-scratch/ihbas/.cache/swebench_singularity
```

### List by Repository

```bash
# Astropy containers
ls -lh /fs/nexus-scratch/ihbas/.cache/swebench_singularity/astropy/*.sif

# Scikit-learn containers
ls -lh /fs/nexus-scratch/ihbas/.cache/swebench_singularity/scikit-learn/*.sif
```

### Recently Built Containers

```bash
# Sort by modification time (newest first)
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" -type f -printf "%T+ %p\n" | sort -r | head -10
```

## Docker Hub Rate Limits

### Rate Limit Quotas

| Account Type | Pulls per 6 hours |
|-------------|-------------------|
| Anonymous   | 100               |
| Free        | 200               |
| Pro/Team    | Unlimited         |

### Check Your Rate Limit Status

```bash
# Check remaining pulls (requires Docker credentials)
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | jq -r .token)
curl -s -H "Authorization: Bearer $TOKEN" https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest -I | grep -i ratelimit
```

### When You Hit Rate Limits

**Error messages you might see:**
```
toomanyrequests: You have reached your pull rate limit
ERROR: 429 Too Many Requests
rate limit exceeded
```

## Solutions for Rate Limits

### 1. Use Cached Containers (Best Option)

The Streamlit app now shows cached containers in the sidebar:

**SWE-bench Mode:**
- Automatically uses cache if available
- Shows "✅ Container ready (cached)" when using cache

**Custom Mode:**
- Select "Browse Cache" as container source
- Choose from your 20 pre-built containers
- Group by repository for easy navigation

### 2. Authenticate with Docker Hub

Set credentials in your environment:

```bash
# For Singularity
export SINGULARITY_DOCKER_USERNAME="your_username"
export SINGULARITY_DOCKER_PASSWORD="your_password"

# For Apptainer
export APPTAINER_DOCKER_USERNAME="your_username"
export APPTAINER_DOCKER_PASSWORD="your_password"

# Restart Streamlit
streamlit run streamlit/app.py
```

### 3. Use Alternative Registries

Instead of Docker Hub, try:

```bash
# GitHub Container Registry (no rate limits for public images)
ghcr.io/owner/image:tag

# Red Hat Quay
quay.io/organization/image:tag

# AWS ECR Public
public.ecr.aws/owner/image:tag
```

### 4. Wait and Retry

Rate limits reset after 6 hours. You can:
- Run tests on host (disable container)
- Use cached containers
- Schedule builds during off-peak hours

## Using Cached Containers in Streamlit

### SWE-bench Mode

1. Enable "Use Singularity Container" (default: ON)
2. Select an instance
3. Click "Run Analysis"
4. **Automatic behavior:**
   - ✅ Checks cache first
   - ✅ Uses cached container if available
   - ⚠️ Only pulls from Docker Hub if not cached

### Custom Codebase Mode

1. Enable "Use Singularity Container"
2. Select **"Browse Cache"** as container source
3. Choose repository: `astropy`, `scikit-learn`, etc.
4. Select specific container from dropdown
5. Upload your code and patch
6. Run analysis with cached container

## Cache Management

### View Cache Statistics

```bash
# Total containers
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" | wc -l

# Cache size
du -sh /fs/nexus-scratch/ihbas/.cache/swebench_singularity

# Breakdown by repository
du -sh /fs/nexus-scratch/ihbas/.cache/swebench_singularity/*/
```

### Clean Old Containers

```bash
# Find containers older than 30 days
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" -mtime +30

# Delete old containers (BE CAREFUL!)
find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" -mtime +30 -delete
```

### Rebuild Specific Container

```bash
# Force rebuild a specific instance
python scripts/swebench_cache_manager.py --rebuild --instance astropy__astropy-12907
```

## Troubleshooting

### Issue: Container Not Found in Cache

**Check if it exists:**
```bash
ls -lh /fs/nexus-scratch/ihbas/.cache/swebench_singularity/**/instance-name.sif
```

**Solution**: Build it first via SLURM or Streamlit

### Issue: Permission Denied

**Check permissions:**
```bash
ls -ld /fs/nexus-scratch/ihbas/.cache/swebench_singularity
```

**Solution**: Ensure you have read/write access to cache directory

### Issue: Corrupted Container

**Verify container:**
```bash
singularity inspect /path/to/container.sif
```

**Solution**: Delete and rebuild:
```bash
rm /path/to/corrupted.sif
# Rebuild via Streamlit or scripts
```

### Issue: NFS Mount Problems

**Check mount:**
```bash
df -h /fs/nexus-scratch
mount | grep nexus-scratch
```

**Solution**: Contact cluster admin if NFS is down

## Best Practices

### 1. Check Cache First
Always check if a container exists before building:

```python
# In your scripts
from pathlib import Path

cache_dir = Path("/fs/nexus-scratch/ihbas/.cache/swebench_singularity")
container = cache_dir / "astropy" / "astropy__astropy-12907.sif"

if container.exists():
    print(f"Using cached container: {container}")
else:
    print("Building new container...")
```

### 2. Build Containers in Batch

Pre-build containers for all instances you'll test:

```bash
# Submit batch build job
sbatch --array=1-20 scripts/slurm_worker_build.sh
```

### 3. Monitor Cache Size

Set up weekly cleanup:

```bash
# Crontab: Clean containers older than 60 days every Sunday
0 0 * * 0 find /fs/nexus-scratch/ihbas/.cache/swebench_singularity -name "*.sif" -mtime +60 -delete
```

### 4. Authenticate for Heavy Usage

If building many containers, authenticate to avoid rate limits:

```bash
# Add to ~/.bashrc
export SINGULARITY_DOCKER_USERNAME="your_username"
export SINGULARITY_DOCKER_PASSWORD="your_password"
```

## Current Cache Status (As of Jan 13, 2026)

```
Total containers: 20
Repositories: astropy (10), scikit-learn (10)
Total size: 23 GB
Location: /fs/nexus-scratch/ihbas/.cache/swebench_singularity/

Latest builds:
- astropy__astropy-13977.sif (Jan 9, 2026)
- astropy__astropy-14309.sif (Jan 9, 2026)
- scikit-learn__scikit-learn-13135.sif (Dec 8, 2025)
```

## Quick Commands Reference

```bash
# List all containers
find /fs/nexus-scratch/ihbas/.cache -name "*.sif"

# Count by repo
find /fs/nexus-scratch/ihbas/.cache -name "*.sif" | cut -d'/' -f8 | sort | uniq -c

# Total cache size
du -sh /fs/nexus-scratch/ihbas/.cache/swebench_singularity

# Recently used
ls -lt /fs/nexus-scratch/ihbas/.cache/swebench_singularity/**/*.sif | head -10

# Find specific instance
find /fs/nexus-scratch/ihbas/.cache -name "*astropy-12907*"

# Verify container works
singularity exec container.sif python --version
```

## Related Documentation

- [STREAMLIT_DEMO_ARCHITECTURE.md](./STREAMLIT_DEMO_ARCHITECTURE.md) - App architecture
- [SWEBENCH_SINGULARITY_RUNNER.md](./SWEBENCH_SINGULARITY_RUNNER.md) - Container execution details
- [INTEGRATED_PIPELINE_GUIDE.md](./INTEGRATED_PIPELINE_GUIDE.md) - Full pipeline docs
