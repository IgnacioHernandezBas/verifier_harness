#!/usr/bin/env python3
"""Test the full pipeline: install + run tests."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.test_patch_singularity import (
    install_package_in_singularity,
    run_tests_in_singularity
)

# Test with the existing pytest repo
repo_path = Path("/fs/nexus-scratch/ihbas/verifier_harness/repos_temp/pytest-dev__pytest")
image_path = "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif"

# Sample tests from the notebook
tests = ["testing/logging/test_fixture.py::test_clear_for_call_stage"]

if repo_path.exists():
    print("="*80)
    print("STEP 1: Install Package")
    print("="*80)
    install_result = install_package_in_singularity(repo_path, image_path)
    print(f"✓ Installed: {install_result['installed']}\n")

    print("="*80)
    print("STEP 2: Run Tests")
    print("="*80)
    test_result = run_tests_in_singularity(
        repo_path=repo_path,
        tests=tests,
        image_path=image_path
    )

    print(f"\nReturn code: {test_result['returncode']}")
    print(f"\nSTDOUT:\n{test_result['stdout']}")
    if test_result['stderr']:
        print(f"\nSTDERR:\n{test_result['stderr'][:500]}")

    if test_result['returncode'] == 0:
        print("\n✅ TESTS PASSED!")
    else:
        print(f"\n❌ TESTS FAILED (exit code {test_result['returncode']})")
else:
    print(f"❌ Repository not found: {repo_path}")
