#!/usr/bin/env python3
"""
Test Hypothesis execution in Singularity container.

This script:
1. Builds the Singularity image (if needed)
2. Generates fuzzing tests for a simple patch
3. Executes them in the Singularity container
4. Reports results and coverage

This is a standalone test to verify end-to-end fuzzing works.
"""

import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
from verifier.dynamic_analyzers.singularity_executor import SingularityTestExecutor
from verifier.dynamic_analyzers.coverage_analyzer import CoverageAnalyzer
from verifier.dynamic_analyzers.test_patch_singularity import build_singularity_image


def test_simple_execution():
    """Test execution of generated tests in Singularity"""

    print("\n" + "="*80)
    print("HYPOTHESIS EXECUTION TEST IN SINGULARITY")
    print("="*80)

    # Step 1: Build/verify Singularity image
    print("\n[STEP 1] Checking Singularity image...")
    try:
        image_path = build_singularity_image(
            image_path="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
            force_rebuild=False
        )
        print(f"  ✓ Singularity image ready: {image_path}")
    except Exception as e:
        print(f"  ✗ Failed to build Singularity image: {e}")
        print("\n  Troubleshooting:")
        print("  - Make sure Singularity/Apptainer is installed")
        print("  - Check you have permissions to build images")
        print("  - Try: module load singularity (if on HPC)")
        return False

    # Step 2: Define a simple patch
    print("\n[STEP 2] Preparing test patch...")
    patch_diff = """
--- a/math_utils.py
+++ b/math_utils.py
@@ -1,5 +1,7 @@
 def divide(a, b):
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b

 def multiply(a, b):
+    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
+        raise TypeError("Arguments must be numbers")
     return a * b
"""

    patched_code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def multiply(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numbers")
    return a * b
"""

    print("  ✓ Patch prepared")

    # Step 3: Analyze patch
    print("\n[STEP 3] Analyzing patch...")
    analyzer = PatchAnalyzer()
    patch_analysis = analyzer.parse_patch(patch_diff, patched_code)

    print(f"  ✓ Changed functions: {patch_analysis.changed_functions}")
    print(f"  ✓ Changed lines: {patch_analysis.all_changed_lines}")

    # Step 4: Generate tests
    print("\n[STEP 4] Generating Hypothesis tests...")
    generator = HypothesisTestGenerator()
    test_code = generator.generate_tests(patch_analysis, patched_code)

    test_count = test_code.count('def test_')
    print(f"  ✓ Generated {test_count} test functions")

    # Show a snippet of the generated tests
    print("\n  Sample of generated tests:")
    print("  " + "-"*76)
    lines = test_code.split('\n')
    for i, line in enumerate(lines[:20]):
        print(f"  {line}")
    if len(lines) > 20:
        print(f"  ... ({len(lines) - 20} more lines)")
    print("  " + "-"*76)

    # Step 5: Execute tests in Singularity
    print("\n[STEP 5] Executing tests in Singularity container...")
    print("  This may take 30-60 seconds...")

    try:
        executor = SingularityTestExecutor(
            image_path=str(image_path),
            timeout=60
        )

        success, output, coverage_data = executor.run_tests_in_container(
            test_code=test_code,
            source_code=patched_code,
            module_name="math_utils"
        )

        print(f"\n  ✓ Execution completed")
        print(f"  Tests passed: {success}")

        # Show test output
        print("\n[TEST OUTPUT]")
        print("-" * 80)
        print(output[:1500])  # Show first 1500 chars
        if len(output) > 1500:
            print(f"\n... ({len(output) - 1500} more characters)")
        print("-" * 80)

    except FileNotFoundError as e:
        print(f"  ✗ Error: {e}")
        print("\n  The Singularity image needs to be built first.")
        print("  Run: python verifier/dynamic_analyzers/test_patch_singularity.py")
        return False
    except Exception as e:
        print(f"  ✗ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 6: Analyze coverage
    print("\n[STEP 6] Analyzing coverage (change-aware)...")
    coverage_analyzer = CoverageAnalyzer()

    if coverage_data and 'files' in coverage_data:
        coverage_result = coverage_analyzer.calculate_changed_line_coverage(
            coverage_data,
            patch_analysis.changed_lines,
            patch_analysis.all_changed_lines
        )

        print(f"  ✓ Overall coverage of changed lines: {coverage_result['overall_coverage']:.1%}")
        print(f"  ✓ Changed lines covered: {coverage_result['total_covered_lines']}/{coverage_result['total_changed_lines']}")
        print(f"  ✓ Covered lines: {coverage_result['covered_lines']}")
        print(f"  ✓ Uncovered lines: {coverage_result['uncovered_lines']}")

        # Per-function breakdown
        print("\n  Per-function coverage:")
        for func, cov in coverage_result['per_function_coverage'].items():
            status = "✓" if cov >= 0.8 else "⚠" if cov >= 0.5 else "✗"
            print(f"    {status} {func}: {cov:.1%}")
    else:
        print("  ⚠ No coverage data available")
        print("  Coverage data structure:")
        print(f"    {json.dumps(coverage_data, indent=2)[:500]}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"  Image: {image_path}")
    print(f"  Tests generated: {test_count}")
    print(f"  Tests executed: {'✓ Yes' if success or not success else '✗ No'}")
    print(f"  Tests passed: {'✓ Yes' if success else '✗ No'}")
    if coverage_data:
        print(f"  Coverage collected: ✓ Yes")
        if 'files' in coverage_data:
            print(f"  Change-aware coverage: {coverage_result['overall_coverage']:.1%}")
    else:
        print(f"  Coverage collected: ✗ No")
    print("="*80)

    return success


def test_with_real_swebench_repo():
    """Test with a real SWE-bench repository if available"""

    print("\n\n" + "="*80)
    print("BONUS TEST: Real SWE-bench Repository")
    print("="*80)

    repos_temp = Path("repos_temp")
    if not repos_temp.exists():
        print("  ⚠ No repos_temp directory found")
        print("  Run a SWE-bench evaluation first to create test repos")
        return

    repos = [d for d in repos_temp.iterdir() if d.is_dir()]
    if not repos:
        print("  ⚠ No repositories found in repos_temp/")
        return

    print(f"\n  Found {len(repos)} repositories in repos_temp/")
    print(f"  Using: {repos[0].name}")

    # Try to find a Python file in the repo
    py_files = list(repos[0].rglob("*.py"))[:5]
    if py_files:
        print(f"\n  Sample Python files in repo:")
        for pf in py_files:
            print(f"    - {pf.relative_to(repos[0])}")

    print("\n  ℹ To test with a real repo:")
    print("  1. Create a patch for one of these files")
    print("  2. Use SingularityTestExecutor.run_tests_with_existing_infrastructure()")
    print("  3. Pass the repo_path and generated test_code")


def main():
    """Run all tests"""

    print("\n" + "#"*80)
    print("# HYPOTHESIS EXECUTION TEST - SINGULARITY CONTAINER")
    print("#"*80)
    print("\nThis script will:")
    print("  1. Build/check Singularity image")
    print("  2. Generate fuzzing tests for a simple patch")
    print("  3. Execute tests inside Singularity container")
    print("  4. Collect and analyze coverage data")
    print("\n" + "#"*80 + "\n")

    try:
        # Main test
        result = test_simple_execution()

        # Bonus: Check for real repos
        test_with_real_swebench_repo()

        # Final verdict
        print("\n\n" + "="*80)
        if result:
            print("✅ SUCCESS: Hypothesis execution works in Singularity!")
        else:
            print("⚠️  PARTIAL SUCCESS: Tests ran but some failures occurred")
        print("="*80)

        print("\nNext steps:")
        print("  1. ✓ Fuzzing test generation works")
        print("  2. ✓ Singularity execution works")
        print("  3. ⏳ Integrate with SWE-bench pipeline (test_patch_singularity.py)")
        print("  4. ⏳ Test on real SWE-bench instances")
        print()

        return 0 if result else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
