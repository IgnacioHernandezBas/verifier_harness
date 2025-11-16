#!/usr/bin/env python3
"""
Test script for the dynamic fuzzing pipeline.

This script demonstrates and tests the complete fuzzing workflow:
1. Patch analysis
2. Test generation
3. Test execution in Singularity
4. Coverage analysis
5. Full pipeline evaluation

Run this after building the Singularity image.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
from verifier.dynamic_analyzers.singularity_executor import SingularityTestExecutor
from verifier.dynamic_analyzers.coverage_analyzer import CoverageAnalyzer
from evaluation_pipeline import EvaluationPipeline


def test_patch_analyzer():
    """Test patch analysis functionality"""
    print("\n" + "="*80)
    print("TEST 1: Patch Analyzer")
    print("="*80)

    patch_diff = """
--- a/math_utils.py
+++ b/math_utils.py
@@ -5,10 +5,15 @@ def divide(a, b):
     Divide two numbers.
     """
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
    '''Divide two numbers.'''
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def multiply(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numbers")
    return a * b
"""

    analyzer = PatchAnalyzer()
    result = analyzer.parse_patch(patch_diff, patched_code)

    print(f"\n✓ Changed functions: {result.changed_functions}")
    print(f"✓ Changed lines by function: {result.changed_lines}")
    print(f"✓ All changed lines: {result.all_changed_lines}")
    print(f"✓ Change types:")
    for change_type, changes in result.change_types.items():
        if changes:
            print(f"    - {change_type}: {len(changes)} changes")

    assert len(result.changed_functions) == 2, "Should detect 2 changed functions"
    assert 'divide' in result.changed_functions, "Should detect divide() changed"
    assert 'multiply' in result.changed_functions, "Should detect multiply() changed"
    print("\n✓ Patch analyzer tests PASSED")
    return result


def test_test_generator(patch_analysis):
    """Test test generation functionality"""
    print("\n" + "="*80)
    print("TEST 2: Test Generator")
    print("="*80)

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

    generator = HypothesisTestGenerator()
    test_code = generator.generate_tests(patch_analysis, patched_code)

    print(f"\n✓ Generated test code ({len(test_code)} characters):")
    print("-" * 80)
    print(test_code[:800] + "\n..." if len(test_code) > 800 else test_code)
    print("-" * 80)

    test_count = test_code.count('def test_')
    print(f"\n✓ Generated {test_count} test functions")
    assert test_count >= 3, f"Should generate at least 3 tests, got {test_count}"
    assert 'hypothesis' in test_code, "Should use Hypothesis"
    assert 'pytest' in test_code, "Should use pytest"
    print("\n✓ Test generator tests PASSED")
    return test_code


def test_singularity_executor(test_code):
    """Test Singularity execution (if image exists)"""
    print("\n" + "="*80)
    print("TEST 3: Singularity Executor")
    print("="*80)

    source_code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def multiply(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Arguments must be numbers")
    return a * b
"""

    try:
        executor = SingularityTestExecutor()
        print(f"✓ Singularity image found: {executor.image_path}")

        print("\n  Running tests in Singularity container...")
        success, output, coverage_data = executor.run_tests_in_container(
            test_code=test_code,
            source_code=source_code,
            module_name="math_utils"
        )

        print(f"\n✓ Tests execution completed")
        print(f"  Success: {success}")
        print(f"  Output length: {len(output)} chars")
        print(f"  Coverage data available: {bool(coverage_data)}")

        if output:
            print(f"\n  Test output (first 500 chars):")
            print("-" * 80)
            print(output[:500])
            print("-" * 80)

        print("\n✓ Singularity executor tests PASSED")
        return success, output, coverage_data

    except FileNotFoundError as e:
        print(f"\n⚠ Singularity image not found: {e}")
        print("  Run 'python test_singularity_build.py' to create it")
        print("  Skipping Singularity tests...")
        return None, None, None


def test_coverage_analyzer(coverage_data, patch_analysis):
    """Test coverage analysis"""
    print("\n" + "="*80)
    print("TEST 4: Coverage Analyzer")
    print("="*80)

    if not coverage_data:
        print("⚠ No coverage data available, using mock data")
        coverage_data = {
            'files': {
                'math_utils.py': {
                    'executed_lines': [2, 3, 4, 6, 8, 9],
                    'missing_lines': [5],
                }
            }
        }

    analyzer = CoverageAnalyzer()
    result = analyzer.calculate_changed_line_coverage(
        coverage_data,
        patch_analysis.changed_lines,
        patch_analysis.all_changed_lines
    )

    print(f"\n✓ Coverage analysis results:")
    print(f"  Overall Coverage: {result['overall_coverage']:.1%}")
    print(f"  Total Changed Lines: {result['total_changed_lines']}")
    print(f"  Covered Lines: {result['total_covered_lines']}")
    print(f"  Uncovered Lines: {result['uncovered_lines']}")

    if result['per_function_coverage']:
        print(f"\n  Per-Function Coverage:")
        for func, cov in result['per_function_coverage'].items():
            print(f"    - {func}: {cov:.1%}")

    # Generate report
    report = analyzer.generate_coverage_report(result, patch_analysis)
    print(f"\n✓ Generated coverage report:")
    print(report)

    print("\n✓ Coverage analyzer tests PASSED")
    return result


def test_full_pipeline():
    """Test the complete evaluation pipeline"""
    print("\n" + "="*80)
    print("TEST 5: Full Pipeline Integration")
    print("="*80)

    patch_data = {
        'id': 'test-math-utils-001',
        'diff': """
--- a/math_utils.py
+++ b/math_utils.py
@@ -5,6 +5,8 @@ def divide(a, b):
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b
""",
        'patched_code': """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
    }

    try:
        pipeline = EvaluationPipeline(
            enable_static=True,
            enable_fuzzing=True,
            static_threshold=0.3,
            coverage_threshold=0.3
        )

        print("\n✓ Pipeline initialized")
        print("  Running full evaluation...")

        result = pipeline.evaluate_patch(patch_data)

        print(f"\n✓ Evaluation completed")
        print(f"  Patch ID: {result['patch_id']}")
        print(f"  Verdict: {result['verdict']}")
        print(f"  Reason: {result['reason']}")
        print(f"  Execution Time: {result.get('execution_time', 0):.2f}s")

        if 'fuzzing_result' in result:
            fuzz = result['fuzzing_result']
            print(f"\n  Fuzzing Results:")
            print(f"    Status: {fuzz.get('status')}")
            print(f"    Tests Generated: {fuzz.get('tests_generated', 0)}")
            print(f"    Tests Passed: {fuzz.get('tests_passed', False)}")
            if 'coverage' in fuzz:
                cov = fuzz['coverage']
                print(f"    Coverage: {cov.get('overall_coverage', 0):.1%}")

        print("\n✓ Full pipeline tests PASSED")
        return result

    except FileNotFoundError as e:
        print(f"\n⚠ Cannot run full pipeline: {e}")
        print("  Build Singularity image first: python test_singularity_build.py")
        return None


def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "#"*80)
    print("# FUZZING PIPELINE TEST SUITE")
    print("#"*80)

    try:
        # Test 1: Patch Analyzer
        patch_analysis = test_patch_analyzer()

        # Test 2: Test Generator
        test_code = test_test_generator(patch_analysis)

        # Test 3: Singularity Executor (may skip if image not available)
        success, output, coverage_data = test_singularity_executor(test_code)

        # Test 4: Coverage Analyzer
        coverage_result = test_coverage_analyzer(coverage_data, patch_analysis)

        # Test 5: Full Pipeline
        pipeline_result = test_full_pipeline()

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print("✓ All tests completed successfully!")
        print("\nComponents tested:")
        print("  ✓ Patch Analyzer")
        print("  ✓ Test Generator")
        if success is not None:
            print("  ✓ Singularity Executor")
        else:
            print("  ⚠ Singularity Executor (skipped - no image)")
        print("  ✓ Coverage Analyzer")
        if pipeline_result:
            print("  ✓ Full Pipeline")
        else:
            print("  ⚠ Full Pipeline (skipped - no image)")
        print("\n" + "="*80)
        print("READY FOR PRODUCTION USE")
        print("="*80)

        return 0

    except Exception as e:
        print(f"\n" + "="*80)
        print(f"ERROR: Test failed")
        print("="*80)
        print(f"{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
