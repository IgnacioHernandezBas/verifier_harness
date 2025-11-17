#!/usr/bin/env python3
"""Quick test to verify the installation fix works."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.test_patch_singularity import install_package_in_singularity

# Test with the existing pytest repo
repo_path = Path("/fs/nexus-scratch/ihbas/verifier_harness/repos_temp/pytest-dev__pytest")
image_path = "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif"

if repo_path.exists():
    print(f"Testing installation for: {repo_path}")
    result = install_package_in_singularity(repo_path, image_path)

    print("\n" + "="*80)
    print("RESULT")
    print("="*80)
    print(f"Return code: {result['returncode']}")
    print(f"Installed: {result['installed']}")

    if result['returncode'] != 0:
        print("\nSTDERR:")
        print(result['stderr'][-500:])
    else:
        print("\n✅ SUCCESS!")
else:
    print(f"❌ Repository not found: {repo_path}")
