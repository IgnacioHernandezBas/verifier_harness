# Podman Setup Guide for Nexus Cluster

This guide documents the podman configuration for using the scratch0 compute directory on the Nexus cluster.

## Configuration Files

### 1. Storage Configuration: `~/.config/containers/storage.conf`

```ini
[storage]
driver = "overlay"
graphroot = "/scratch0/ihbas/.containers/storage"
runroot = "/scratch0/ihbas/.containers/tmp"

[storage.options.overlay]
mountopt = "nodev,metacopy=on"
# force_mask = "700"  # Commented out - may require mount_program
```

**What this does:**
- Sets podman to use `/scratch0/ihbas/.containers/storage` for persistent image/container storage
- Sets podman to use `/scratch0/ihbas/.containers/tmp` for temporary runtime data
- Uses overlay driver with optimized mount options for shared clusters

### 2. Containers Configuration: `~/.config/containers/containers.conf` (Optional)

If you need additional configuration, create this file:

```ini
[containers]
# Set default ulimits
default_ulimits = [
  "nofile=65536:65536",
]

[engine]
# Use /tmp for temporary files during builds
env = [
  "TMPDIR=/tmp",
]
```

## Directory Structure

After configuration, your podman directories will be:

```
/scratch0/ihbas/.containers/
├── storage/          # Images and container layers
│   ├── overlay/      # Overlay filesystem layers
│   ├── overlay-containers/
│   ├── overlay-images/
│   ├── overlay-layers/
│   └── db.sql        # Storage database
└── tmp/              # Runtime temporary files
```

## Useful Commands

### Basic Operations

```bash
# List all images
podman images

# List all containers (running and stopped)
podman ps -a

# List only running containers
podman ps

# Pull an image
podman pull python:3.11-slim

# Build an image from a Dockerfile
podman build -t my-image:tag /path/to/dockerfile/directory

# Run a container
podman run --rm -it image-name bash

# Run a command in a container
podman run --rm image-name python -c "print('Hello')"
```

### Cleanup Commands

```bash
# Remove unused images
podman image prune

# Remove all unused images (not just dangling)
podman image prune -a

# Remove stopped containers
podman container prune

# Remove all unused data (containers, images, networks, volumes)
podman system prune -a

# Check disk usage
podman system df
```

### Troubleshooting Commands

```bash
# Check podman configuration and system info
podman info

# Check podman version
podman --version

# List active mounts (useful for debugging)
mount | grep $USER | grep overlay

# If you get "cannot re-exec process" error, try these in order:
# 1. Trigger automatic cleanup
podman ps -a

# 2. System prune
podman system prune -a

# 3. Reset podman (WARNING: removes all images and containers)
podman system reset --force

# 4. Nuclear option - manually clean storage (only if podman commands fail)
podman unshare rm -rf /scratch0/ihbas/.containers/storage/*
```

### Container Management

```bash
# Stop a running container
podman stop <container-id>

# Remove a container
podman rm <container-id>

# Remove a container forcefully
podman rm -f <container-id>

# Remove an image
podman rmi <image-id>

# Remove an image forcefully
podman rmi -f <image-id>

# Inspect an image or container
podman inspect <image-or-container-id>

# View logs from a container
podman logs <container-id>

# Execute command in running container
podman exec -it <container-id> bash
```

### Advanced Operations

```bash
# Enter podman's user namespace (useful for debugging permissions)
podman unshare

# Export a container filesystem as tar archive
podman export <container-id> -o container.tar

# Import a tar archive as an image
podman import container.tar my-image:tag

# Save image to tar file
podman save -o image.tar image-name:tag

# Load image from tar file
podman load -i image.tar

# Copy files from container to host
podman cp <container-id>:/path/in/container /path/on/host

# Copy files from host to container
podman cp /path/on/host <container-id>:/path/in/container
```

## Environment Variables

Useful environment variables for podman:

```bash
# Set temporary directory for builds
export TMPDIR=/tmp

# Override storage configuration file location
export CONTAINERS_STORAGE_CONF=~/.config/containers/storage.conf

# Override containers configuration file location
export CONTAINERS_CONF=~/.config/containers/containers.conf
```

## Common Issues and Solutions

### Issue: "cannot re-exec process to join the existing user namespace"

**Symptoms:** Podman commands fail with namespace errors

**Solutions (try in order):**
1. Run `podman ps -a` to trigger automatic cleanup
2. Run `podman system prune -a` to remove unused data
3. Run `podman system reset --force` (WARNING: removes everything)
4. Use `podman unshare rm -rf /scratch0/ihbas/.containers/storage/*` to manually clean

### Issue: "Permission denied" when removing storage files

**Cause:** Overlay filesystem mounts have different permissions inside user namespace

**Solution:** Use `podman unshare` to enter the user namespace:
```bash
podman unshare rm -rf /scratch0/ihbas/.containers/storage/overlay
```

### Issue: "Device or resource busy" when cleaning storage

**Cause:** Container layers are still mounted

**Solution:**
1. Stop all containers: `podman stop -a`
2. Remove all containers: `podman rm -a`
3. Try cleanup again: `podman system prune -a`

### Issue: Disk space running out

**Check usage:**
```bash
# Check podman disk usage
podman system df

# Check scratch0 disk space
df -h /scratch0
```

**Clean up:**
```bash
# Remove dangling images
podman image prune

# Remove all unused images
podman image prune -a

# Full cleanup
podman system prune -a --volumes
```

## Best Practices

1. **Regular Cleanup:** Run `podman system prune` periodically to free up space
2. **Use --rm flag:** When running temporary containers, use `--rm` to auto-remove them
3. **Layer Caching:** Order Dockerfile commands from least to most frequently changing for better caching
4. **Small Base Images:** Use slim/alpine variants when possible (e.g., `python:3.11-slim`)
5. **Build Context:** Keep Dockerfile context small to speed up builds
6. **Clean Builds:** Use `--no-cache` if you need a fresh build: `podman build --no-cache`

## Disk Space Management

Monitor your usage on scratch0:

```bash
# Check total space
df -h /scratch0

# Check podman usage breakdown
podman system df -v

# See largest images
podman images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | sort -k2 -h
```

## Configuration Verification

To verify your setup is correct:

```bash
# Check storage configuration
podman info | grep -A 10 "graphRoot\|runRoot"

# Expected output:
#   graphRoot: /scratch0/ihbas/.containers/storage
#   runRoot: /scratch0/ihbas/.containers/tmp

# Test with a simple container
podman run --rm alpine:latest echo "Podman is working!"
```

## Quick Reference

| Task | Command |
|------|---------|
| List images | `podman images` |
| List containers | `podman ps -a` |
| Build image | `podman build -t name:tag .` |
| Run container | `podman run --rm -it image bash` |
| Stop container | `podman stop <id>` |
| Remove container | `podman rm <id>` |
| Remove image | `podman rmi <id>` |
| Clean up all | `podman system prune -a` |
| Check disk usage | `podman system df` |
| View config | `podman info` |
| Reset everything | `podman system reset --force` |

## Additional Resources

- Podman official docs: https://docs.podman.io/
- Containers config docs: https://github.com/containers/common/blob/main/docs/containers.conf.5.md
- Storage config docs: https://github.com/containers/storage/blob/main/docs/containers-storage.conf.5.md

---

**Last Updated:** 2025-11-10
**Cluster:** Nexus
**User:** ihbas
**Storage Location:** /scratch0/ihbas/.containers/
