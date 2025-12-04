#!/usr/bin/env python3
"""
SLURM worker script for building a single container.
Called by the SLURM batch script with an instance ID.
"""

import os
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: slurm_worker_build.py <instance_id>")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    
    # Import after setting environment variables
    from swebench_singularity import Config, SingularityBuilder
    
    print(f"Building container for: {instance_id}")
    
    # Initialize config
    config = Config()
    config.set("singularity.cache_dir", "/fs/nexus-scratch/ihbas/.cache/swebench_singularity")
    config.set("singularity.tmp_dir", "/fs/nexus-scratch/ihbas/.tmp/singularity_build")
    config.set("singularity.cache_internal_dir", "/fs/nexus-scratch/ihbas/.singularity/cache")
    config.set("singularity.build_timeout", 3600)  # 1 hour for slow networks
    config.set("docker.max_retries", 3)
    
    # Use correct SWE-bench image pattern
    config.set("docker.image_patterns", [
        "swebench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest",
    ])
    
    # Build the container
    builder = SingularityBuilder(config)
    result = builder.build_instance(
        instance_id=instance_id,
        force_rebuild=False,
        check_docker_exists=False
    )
    
    if result.success:
        print(f"✓ SUCCESS: {instance_id}")
        print(f"  Path: {result.sif_path}")
        print(f"  Build time: {result.build_time_seconds:.1f}s")
        print(f"  From cache: {result.from_cache}")
        return 0
    else:
        print(f"✗ FAILED: {instance_id}")
        print(f"  Error: {result.error_message}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
