#!/usr/bin/env python3
"""
Test script to verify pytest installation in Singularity containers works.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from swebench_integration import DatasetLoader
from verifier.dynamic_analyzers.test_patch_singularity import run_tests_in_singularity

# Test configuration
INSTANCE_ID = "scikit-learn__scikit-learn-10297"
CONTAINER_IMAGE_PATH = "/fs/nexus-scratch/ihbas/.cache/swebench_singularity/scikit-learn/scikit-learn__scikit-learn-10297.sif"
REPO_PATH = Path("/fs/nexus-scratch/ihbas/verifier_harness/repos_temp/scikit-learn__scikit-learn")

# Simple tests to run
tests = [
    "sklearn/linear_model/tests/test_ridge.py::test_ridge_classifier_cv_store_cv_values"
]

print(f"Testing pytest installation and execution...")
print(f"  Container: {CONTAINER_IMAGE_PATH}")
print(f"  Repo: {REPO_PATH}")
print(f"  Tests: {tests}\n")

# Verify paths exist
if not Path(CONTAINER_IMAGE_PATH).exists():
    print(f"❌ Container not found: {CONTAINER_IMAGE_PATH}")
    sys.exit(1)

if not REPO_PATH.exists():
    print(f"❌ Repository not found: {REPO_PATH}")
    sys.exit(1)

# Run the test
try:
    result = run_tests_in_singularity(
        repo_path=REPO_PATH,
        tests=tests,
        image_path=CONTAINER_IMAGE_PATH
    )

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Exit code: {result['returncode']}")
    print(f"\nStdout:\n{result['stdout']}")
    print(f"\nStderr:\n{result['stderr']}")

    if result['returncode'] == 0:
        print("\n✓ Tests passed!")
    else:
        print(f"\n⚠️ Tests exited with code {result['returncode']}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
