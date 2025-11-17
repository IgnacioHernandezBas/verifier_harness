#!/usr/bin/env python3
"""
Quick Start Script for SWE-bench Fuzzing

This script provides a simple way to test the fuzzing setup with a single patch.
It's designed to be the easiest entry point for getting started.

Usage:
    python quick_start.py                    # Test with default instance
    python quick_start.py --instance-id ID   # Test specific instance
    python quick_start.py --list            # List available instances
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
    from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
    from verifier.dynamic_analyzers.singularity_executor import SingularityTestExecutor
    from verifier.dynamic_analyzers.coverage_analyzer import CoverageAnalyzer
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Failed to import modules: {e}")
    print("\nPlease run: ./setup_fuzzing.sh")
    sys.exit(1)


def list_available_instances():
    """List some test instances from different repositories."""
    instances = [
        ("matplotlib/matplotlib", "matplotlib__matplotlib-23314"),
        ("scikit-learn/scikit-learn", "scikit-learn__scikit-learn-13241"),
        ("django/django", "django__django-11001"),
        ("sympy/sympy", "sympy__sympy-13971"),
        ("pytest-dev/pytest", "pytest-dev__pytest-5221"),
        ("sphinx-doc/sphinx", "sphinx-doc__sphinx-8506"),
    ]

    print("\n" + "="*60)
    print("Available Test Instances (examples):")
    print("="*60)
    for repo, instance_id in instances:
        print(f"  {repo:30} → {instance_id}")
    print("="*60)
    print("\nUse: python quick_start.py --instance-id <instance_id>")
    print()


def test_single_instance(instance_id: str):
    """Test fuzzing on a single SWE-bench instance."""

    print("\n" + "="*60)
    print(f"Testing Fuzzing Setup: {instance_id}")
    print("="*60 + "\n")

    # Step 1: Check container
    print("Step 1: Checking Singularity container...")
    container_path = Path.home() / ".containers/singularity/verifier-swebench.sif"
    if not container_path.exists():
        # Try alternate location
        scratch_path = Path(os.environ.get('SCRATCH0', '/tmp')) / ".containers/singularity/verifier-swebench.sif"
        if scratch_path.exists():
            container_path = scratch_path
        else:
            print(f"✗ Container not found at {container_path}")
            print("  Please run: python test_singularity_build.py")
            return False

    print(f"✓ Container found: {container_path}")
    print(f"  Size: {container_path.stat().st_size / (1024*1024):.1f} MB\n")

    # Step 2: Parse instance ID
    print("Step 2: Parsing instance ID...")
    try:
        repo_name = instance_id.replace("__", "/", 1).split("-")[0] + "/" + instance_id.split("__")[0].split("-")[-1]
        print(f"✓ Repository: {repo_name}\n")
    except Exception as e:
        print(f"✗ Failed to parse instance ID: {e}")
        return False

    # Step 3: Initialize components
    print("Step 3: Initializing fuzzing components...")
    try:
        patch_analyzer = PatchAnalyzer()
        test_generator = HypothesisTestGenerator()
        executor = SingularityTestExecutor(str(container_path))
        coverage_analyzer = CoverageAnalyzer()
        print("✓ All components initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False

    # Step 4: Show what would happen
    print("Step 4: Fuzzing pipeline ready!")
    print("\nThe full pipeline would:")
    print("  1. Clone repository")
    print("  2. Apply patch")
    print("  3. Extract changed lines")
    print("  4. Generate property-based tests")
    print("  5. Execute tests in Singularity container")
    print("  6. Collect coverage and results")
    print("\nTo run the full pipeline, use:")
    print(f"  python eval_cli.py --instance-id {instance_id}")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Quick start script for SWE-bench fuzzing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--instance-id",
        type=str,
        help="SWE-bench instance ID to test (e.g., django__django-11001)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available test instances"
    )

    args = parser.parse_args()

    if args.list:
        list_available_instances()
        return 0

    # Default instance if none provided
    instance_id = args.instance_id or "matplotlib__matplotlib-23314"

    success = test_single_instance(instance_id)

    if success:
        print("="*60)
        print("✓ Setup verification complete!")
        print("="*60)
        return 0
    else:
        print("="*60)
        print("✗ Setup verification failed")
        print("="*60)
        print("\nTroubleshooting:")
        print("  1. Run: ./setup_fuzzing.sh")
        print("  2. Check: conda activate verifier_env")
        print("  3. Build container: python test_singularity_build.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
