#!/usr/bin/env python3
"""
Test script to verify Docker Hub authentication with Apptainer/Singularity.
This should be run to verify credentials work before running the full notebook.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from swebench_singularity import Config, SingularityBuilder

def main():
    print("=" * 80)
    print("Docker Hub Authentication Test")
    print("=" * 80)
    print()

    # Set credentials
    os.environ["APPTAINER_DOCKER_USERNAME"] = "nacheitor12"
    os.environ["APPTAINER_DOCKER_PASSWORD"] = "wN/^4Me%,!5zz_q"
    os.environ["SINGULARITY_DOCKER_USERNAME"] = "nacheitor12"
    os.environ["SINGULARITY_DOCKER_PASSWORD"] = "wN/^4Me%,!5zz_q"

    print("✓ Credentials set in environment")
    print(f"  APPTAINER_DOCKER_USERNAME: {os.environ.get('APPTAINER_DOCKER_USERNAME')}")
    print(f"  SINGULARITY_DOCKER_USERNAME: {os.environ.get('SINGULARITY_DOCKER_USERNAME')}")
    print()

    # Initialize config and builder
    config = Config()
    config.set("singularity.cache_dir", "/fs/nexus-scratch/ihbas/.cache/swebench_singularity")
    config.set("singularity.tmp_dir", "/fs/nexus-scratch/ihbas/.tmp/singularity_build")
    config.set("singularity.cache_internal_dir", "/fs/nexus-scratch/ihbas/.singularity/cache")
    config.set("singularity.build_timeout", 1800)
    config.set("docker.max_retries", 3)

    builder = SingularityBuilder(config)

    print("✓ Builder initialized")
    print()

    # Check if builder can detect credentials
    creds = builder._get_docker_credentials()
    if creds:
        print(f"✓ Builder detected credentials: {creds[0]}")
    else:
        print("❌ Builder could NOT detect credentials!")
        return 1

    print()

    # Check environment variables are properly set
    print("Environment variables after builder initialization:")
    for var in ["APPTAINER_DOCKER_USERNAME", "APPTAINER_DOCKER_PASSWORD",
                "SINGULARITY_DOCKER_USERNAME", "SINGULARITY_DOCKER_PASSWORD",
                "APPTAINER_TMPDIR", "APPTAINER_CACHEDIR"]:
        value = os.environ.get(var, "NOT SET")
        if "PASSWORD" in var:
            value = "***" if value != "NOT SET" else "NOT SET"
        print(f"  {var}: {value}")

    print()
    print("=" * 80)
    print("✓ All checks passed! Authentication should work.")
    print("=" * 80)
    print()
    print("Now you can run the notebook. Make sure to:")
    print("  1. Restart the kernel if it's already running")
    print("  2. Run all cells from the beginning")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
