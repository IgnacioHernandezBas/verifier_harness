#!/usr/bin/env python3
"""
Differential Validation Script for Claim C1 (astropy__astropy-7746)

This script validates Claim C1 by running the test in two configurations:
- C_bug: base_commit without patch (test should FAIL)
- C_gold: base_commit + gold patch (test should PASS)
"""

import sys
import json
from pathlib import Path
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from swebench_integration import DatasetLoader, PatchLoader
from verifier.dynamic_analyzers import test_patch_singularity
from swebench_singularity import SingularityBuilder, Config

INSTANCE_ID = "astropy__astropy-7746"
CLAIM_ID = "C1"
CLAIM_TEST_PATH = "claim_tests/astropy__astropy-7746"


def sync_claim_tests_into_repo(instance_id: str, repo_path: Path) -> Path:
    """Copy claim-tests into the repo so they're visible in Singularity."""
    claim_tests_root = PROJECT_ROOT / "claim-tests"
    src_dir = claim_tests_root / instance_id

    if not src_dir.exists():
        raise FileNotFoundError(f"No claim-tests found for {instance_id} at {src_dir}")

    dest_dir = repo_path / "claim_tests" / instance_id
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    # Replace existing copy
    if dest_dir.exists():
        shutil.rmtree(dest_dir)

    shutil.copytree(src_dir, dest_dir)
    print(f"✅ Synced claim-tests from {src_dir} to {dest_dir}")
    return dest_dir


def run_claim_test_in_singularity(repo_path: Path, container_path: Path) -> dict:
    """Run claim-tests in Singularity container."""
    print(f"\n🐳 Running tests in container: {container_path.name}")

    # Install dependencies
    print("📦 Installing package dependencies...")
    install_result = test_patch_singularity.install_package_in_singularity(
        repo_path=repo_path,
        image_path=str(container_path)
    )

    if install_result.get('returncode') != 0:
        print(f"⚠️  Dependency installation had warnings")

    # Run claim-tests
    print(f"🧪 Running claim-tests at {CLAIM_TEST_PATH}...")
    test_result = test_patch_singularity.run_tests_in_singularity(
        repo_path=repo_path,
        tests=[CLAIM_TEST_PATH],  # Relative path inside /workspace
        image_path=str(container_path),
        collect_coverage=False,
        verbose=True,
        test_framework_hint="pytest"
    )

    # Parse results
    import re
    stdout = test_result.get('stdout', '')
    stderr = test_result.get('stderr', '')
    returncode = test_result.get('returncode', -1)

    passed = int(re.search(r'(\d+) passed', stdout).group(1)) if re.search(r'(\d+) passed', stdout) else 0
    failed = int(re.search(r'(\d+) failed', stdout).group(1)) if re.search(r'(\d+) failed', stdout) else 0
    errors = int(re.search(r'(\d+) error', stdout).group(1)) if re.search(r'(\d+) error', stdout) else 0

    return {
        'success': returncode == 0,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'total': passed + failed + errors,
        'stdout': stdout,
        'stderr': stderr,
        'returncode': returncode
    }


def main():
    print("=" * 80)
    print(f"🔬 Differential Validation: {INSTANCE_ID} - Claim {CLAIM_ID}")
    print("=" * 80)

    # Step 1: Load instance data
    print("\n📥 Loading instance data from SWE-bench Lite...")
    loader = DatasetLoader('princeton-nlp/SWE-bench_Lite', hf_mode=True, split='test')

    sample = None
    for s in loader.iter_samples():
        if s['metadata'].get('instance_id') == INSTANCE_ID:
            sample = s
            break

    if not sample:
        print(f"❌ Instance {INSTANCE_ID} not found in dataset")
        return 1

    print(f"✅ Found instance: {INSTANCE_ID}")
    print(f"   Repo: {sample['repo']}")
    print(f"   Base commit: {sample['base_commit'][:8]}")
    print(f"   Patch length: {len(sample['patch'])} chars")

    # Step 2: Get or build container
    print("\n🏗️  Setting up Singularity container...")
    config = Config()
    builder = SingularityBuilder(config)

    build_result = builder.build_instance(
        instance_id=INSTANCE_ID,
        force_rebuild=False,
        check_docker_exists=False
    )

    if not build_result.success:
        print(f"❌ Container build failed: {build_result.error_message}")
        return 1

    container_path = build_result.sif_path
    print(f"✅ Container ready: {container_path}")

    # Step 3: Setup C_bug (base_commit WITHOUT patch)
    print("\n" + "=" * 80)
    print("🐛 CONFIGURATION: C_bug (base_commit, NO patch)")
    print("=" * 80)

    patcher_bug = PatchLoader(sample=sample, repos_root="repos_temp_demo")
    repo_path_bug = patcher_bug.clone_repository()
    print(f"✅ Repository cloned to: {repo_path_bug}")
    print(f"   Current commit: {sample['base_commit'][:8]} (buggy version)")

    # Sync claim-tests
    sync_claim_tests_into_repo(INSTANCE_ID, Path(repo_path_bug))

    # Run test on C_bug
    result_bug = run_claim_test_in_singularity(Path(repo_path_bug), container_path)

    print(f"\n📊 C_bug Results:")
    print(f"   Passed: {result_bug['passed']}")
    print(f"   Failed: {result_bug['failed']}")
    print(f"   Errors: {result_bug['errors']}")
    print(f"   Return code: {result_bug['returncode']}")

    # Expected: Test should FAIL (detect the bug)
    bug_detected = not result_bug['success']
    if bug_detected:
        print(f"   ✅ EXPECTED: Test FAILED on C_bug (bug detected)")
    else:
        print(f"   ❌ UNEXPECTED: Test PASSED on C_bug (bug NOT detected)")

    # Step 4: Setup C_gold (base_commit + gold patch)
    print("\n" + "=" * 80)
    print("✨ CONFIGURATION: C_gold (base_commit + gold patch)")
    print("=" * 80)

    patcher_gold = PatchLoader(sample=sample, repos_root="repos_temp_demo")
    repo_path_gold = patcher_gold.clone_repository()
    print(f"✅ Repository cloned to: {repo_path_gold}")

    # Apply gold patch
    print(f"📝 Applying gold patch...")
    patch_result = patcher_gold.apply_patch()

    if not patch_result['applied']:
        print(f"❌ Failed to apply gold patch")
        return 1

    print(f"✅ Gold patch applied successfully")

    # Sync claim-tests
    sync_claim_tests_into_repo(INSTANCE_ID, Path(repo_path_gold))

    # Run test on C_gold
    result_gold = run_claim_test_in_singularity(Path(repo_path_gold), container_path)

    print(f"\n📊 C_gold Results:")
    print(f"   Passed: {result_gold['passed']}")
    print(f"   Failed: {result_gold['failed']}")
    print(f"   Errors: {result_gold['errors']}")
    print(f"   Return code: {result_gold['returncode']}")

    # Expected: Test should PASS (fix resolves it)
    fix_works = result_gold['success']
    if fix_works:
        print(f"   ✅ EXPECTED: Test PASSED on C_gold (fix works)")
    else:
        print(f"   ❌ UNEXPECTED: Test FAILED on C_gold (fix doesn't work)")

    # Step 5: Final validation
    print("\n" + "=" * 80)
    print("📋 CLAIM VALIDATION SUMMARY")
    print("=" * 80)

    print(f"\nClaim C1: {CLAIM_ID}")
    print(f"  1. FAIL on C_bug (detects bug):    {'✅ YES' if bug_detected else '❌ NO'}")
    print(f"  2. PASS on C_gold (fix resolves):  {'✅ YES' if fix_works else '❌ NO'}")

    claim_valid = bug_detected and fix_works

    if claim_valid:
        print(f"\n🎉 RESULT: Claim C1 is VALID")
        print(f"   The claim correctly captures the bug and validates the fix.")
    else:
        print(f"\n⚠️  RESULT: Claim C1 is INVALID")
        print(f"   The test does not satisfy differential execution requirements.")

    # Save results
    results_file = PROJECT_ROOT / "results" / f"validation_{INSTANCE_ID}_{CLAIM_ID}.json"
    results_file.parent.mkdir(exist_ok=True)

    validation_results = {
        'instance_id': INSTANCE_ID,
        'claim_id': CLAIM_ID,
        'timestamp': str(Path(__file__).stat().st_mtime),
        'c_bug': {
            'test_failed': bug_detected,
            'passed': result_bug['passed'],
            'failed': result_bug['failed'],
            'errors': result_bug['errors']
        },
        'c_gold': {
            'test_passed': fix_works,
            'passed': result_gold['passed'],
            'failed': result_gold['failed'],
            'errors': result_gold['errors']
        },
        'claim_valid': claim_valid
    }

    with open(results_file, 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    return 0 if claim_valid else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
