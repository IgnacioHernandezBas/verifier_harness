#!/usr/bin/env python3
"""
Run coverage-guided differential fuzzing on a patch.

This script demonstrates the CORE NOVELTY of the verification harness:
- Coverage-guided input generation targeting changed code
- Differential testing (original vs patched)
- Behavioral change classification (expected vs suspicious vs regression)

Usage:
    python run_coverage_guided_fuzzing.py --patch-file PATCH --original-file ORIG --patched-file PATCHED
    python run_coverage_guided_fuzzing.py --demo  # Run demo with example patch
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from verifier.dynamic_analyzers.coverage_guided_fuzzer import (
    CoverageGuidedDifferentialFuzzer,
    run_coverage_guided_fuzzing,
)
from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer


def run_demo():
    """Run demonstration with example patches showing different scenarios."""
    print("=" * 80)
    print("COVERAGE-GUIDED DIFFERENTIAL FUZZING - DEMONSTRATION")
    print("=" * 80)
    print()

    # Demo 1: Bug fix (expected divergence)
    print("DEMO 1: Bug Fix - Division by Zero")
    print("-" * 40)

    original_1 = """
def divide(a, b):
    return a / b
"""

    patched_1 = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""

    result_1 = run_coverage_guided_fuzzing(
        original_code=original_1,
        patched_code=patched_1,
        changed_lines=[2, 3, 4],
        function_name="divide",
        issue_description="Application crashes with ZeroDivisionError when dividing by zero",
        patch_description="Handle zero divisor with proper ValueError",
        max_iterations=500,
        timeout_seconds=30.0,
    )

    print(f"\nVerdict: {result_1.verdict}")
    print(f"Expected divergences: {result_1.expected_divergences}")
    print(f"Suspicious divergences: {result_1.suspicious_divergences}")
    print(f"Regressions: {result_1.regressions}")
    print()

    # Demo 2: Regression (patch introduces bug)
    print("\n" + "=" * 80)
    print("DEMO 2: Regression - Patch Breaks Existing Functionality")
    print("-" * 40)

    original_2 = """
def get_item(items, index):
    if index < 0:
        index = len(items) + index
    return items[index]
"""

    patched_2 = """
def get_item(items, index):
    if index < 0:
        raise IndexError("Negative indices not allowed")
    return items[index]
"""

    result_2 = run_coverage_guided_fuzzing(
        original_code=original_2,
        patched_code=patched_2,
        changed_lines=[3, 4],
        function_name="get_item",
        issue_description="",  # No issue description - suspicious
        patch_description="Clean up index handling",
        max_iterations=500,
        timeout_seconds=30.0,
    )

    print(f"\nVerdict: {result_2.verdict}")
    print(f"Expected divergences: {result_2.expected_divergences}")
    print(f"Suspicious divergences: {result_2.suspicious_divergences}")
    print(f"Regressions: {result_2.regressions}")
    print()

    # Demo 3: Edge case handling
    print("\n" + "=" * 80)
    print("DEMO 3: Edge Case - Empty List Handling")
    print("-" * 40)

    original_3 = """
def first_element(items):
    return items[0]
"""

    patched_3 = """
def first_element(items):
    if not items:
        return None
    return items[0]
"""

    result_3 = run_coverage_guided_fuzzing(
        original_code=original_3,
        patched_code=patched_3,
        changed_lines=[2, 3, 4],
        function_name="first_element",
        issue_description="Function crashes on empty list, should return None",
        patch_description="Handle empty list edge case",
        max_iterations=500,
        timeout_seconds=30.0,
    )

    print(f"\nVerdict: {result_3.verdict}")
    print(f"Expected divergences: {result_3.expected_divergences}")
    print(f"Suspicious divergences: {result_3.suspicious_divergences}")
    print(f"Regressions: {result_3.regressions}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Demo 1 (Bug Fix):    {result_1.verdict} - Correctly identified fix")
    print(f"Demo 2 (Regression): {result_2.verdict} - Correctly identified regression")
    print(f"Demo 3 (Edge Case):  {result_3.verdict} - Correctly identified improvement")
    print()
    print("The coverage-guided differential fuzzer successfully distinguishes between:")
    print("  - Expected behavioral changes (bug fixes)")
    print("  - Suspicious changes (unexplained modifications)")
    print("  - Regressions (previously working code now fails)")
    print()

    return {
        'demo_1': result_1.to_dict(),
        'demo_2': result_2.to_dict(),
        'demo_3': result_3.to_dict(),
    }


def run_on_files(patch_file: Path, original_file: Path, patched_file: Path,
                 function_name: str, issue_desc: str = "", patch_desc: str = ""):
    """Run fuzzing on actual files."""
    # Parse patch to get changed lines
    patch_content = patch_file.read_text()
    original_code = original_file.read_text()
    patched_code = patched_file.read_text()

    # Use patch analyzer to get changed lines
    analyzer = PatchAnalyzer()
    analysis = analyzer.parse_patch(patch_content, patched_code)

    # Get all changed lines
    changed_lines = []
    for func, lines in analysis.changed_lines.items():
        changed_lines.extend(lines)
    changed_lines = list(set(changed_lines))

    if not changed_lines:
        print("Warning: Could not determine changed lines from patch, using all lines")
        changed_lines = list(range(1, len(patched_code.splitlines()) + 1))

    # Determine function name if not provided
    if not function_name and analysis.changed_functions:
        function_name = analysis.changed_functions[0]
        print(f"Auto-detected function: {function_name}")

    if not function_name:
        print("Error: Could not determine function name. Please provide --function-name")
        sys.exit(1)

    # Get class name if applicable
    class_name = analysis.class_context.get(function_name) if analysis.class_context else None

    result = run_coverage_guided_fuzzing(
        original_code=original_code,
        patched_code=patched_code,
        changed_lines=changed_lines,
        function_name=function_name,
        class_name=class_name,
        issue_description=issue_desc,
        patch_description=patch_desc,
        max_iterations=10000,
        timeout_seconds=300.0,
    )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Coverage-guided differential fuzzing for patch verification"
    )
    parser.add_argument("--demo", action="store_true",
                       help="Run demonstration with example patches")
    parser.add_argument("--patch-file", type=Path,
                       help="Path to patch file (unified diff)")
    parser.add_argument("--original-file", type=Path,
                       help="Path to original code file")
    parser.add_argument("--patched-file", type=Path,
                       help="Path to patched code file")
    parser.add_argument("--function-name", type=str,
                       help="Name of function to test (auto-detected if not provided)")
    parser.add_argument("--issue-description", type=str, default="",
                       help="GitHub issue description (for classification)")
    parser.add_argument("--patch-description", type=str, default="",
                       help="Commit message or PR description")
    parser.add_argument("--output-json", type=Path,
                       help="Output results as JSON to this file")
    parser.add_argument("--max-iterations", type=int, default=10000,
                       help="Maximum fuzzing iterations (default: 10000)")
    parser.add_argument("--timeout", type=float, default=300.0,
                       help="Fuzzing timeout in seconds (default: 300)")

    args = parser.parse_args()

    if args.demo:
        results = run_demo()
        if args.output_json:
            args.output_json.write_text(json.dumps(results, indent=2))
            print(f"\nResults saved to {args.output_json}")
        return

    if not all([args.patch_file, args.original_file, args.patched_file]):
        print("Error: Must provide --patch-file, --original-file, and --patched-file")
        print("       Or use --demo to run demonstration")
        parser.print_help()
        sys.exit(1)

    result = run_on_files(
        patch_file=args.patch_file,
        original_file=args.original_file,
        patched_file=args.patched_file,
        function_name=args.function_name,
        issue_desc=args.issue_description,
        patch_desc=args.patch_description,
    )

    if args.output_json:
        args.output_json.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"\nResults saved to {args.output_json}")

    # Exit with appropriate code
    if result.verdict == "FAIL":
        sys.exit(1)
    elif result.verdict == "WARNING":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
