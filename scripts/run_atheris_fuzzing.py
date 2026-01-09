#!/usr/bin/env python3
"""
Run Atheris-based coverage-guided differential fuzzing.

This is the CORE NOVELTY of the verification harness:
- TRUE coverage-guided input generation (Atheris uses coverage feedback to mutate inputs)
- Differential testing in containers (original vs patched)
- Behavioral change classification (expected fix vs suspicious vs regression)

Usage:
    # Run demo
    python scripts/run_atheris_fuzzing.py --demo

    # Run on actual files
    python scripts/run_atheris_fuzzing.py \
        --original-file original.py \
        --patched-file patched.py \
        --function-name my_function \
        --params '[{"name": "x", "type": "int"}, {"name": "y", "type": "str"}]'

    # Run via SLURM
    sbatch scripts/slurm/atheris_fuzz_job.sh
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verifier.dynamic_analyzers.atheris_fuzzer import (
    AtherisDifferentialFuzzer,
    run_atheris_fuzzing,
)


def run_demo():
    """Run demonstration with example patches."""
    print("=" * 80)
    print("ATHERIS COVERAGE-GUIDED DIFFERENTIAL FUZZING - DEMO")
    print("=" * 80)
    print()
    print("This demo shows how coverage-guided fuzzing detects:")
    print("  1. Expected bug fixes")
    print("  2. Regressions (previously working code now fails)")
    print("  3. Suspicious unexplained changes")
    print()

    # Demo 1: Bug fix (expected)
    print("-" * 80)
    print("DEMO 1: Bug Fix - Division by Zero Handling")
    print("-" * 80)

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

    params_1 = [
        {'name': 'a', 'type': 'int'},
        {'name': 'b', 'type': 'int'},
    ]

    print("Original: return a / b")
    print("Patched:  if b == 0: raise ValueError; return a / b")
    print()
    print("Expected behavior: Atheris should find that b=0 now raises ValueError")
    print("                   instead of ZeroDivisionError - this is EXPECTED fix")
    print()

    result_1 = run_atheris_fuzzing(
        original_code=original_1,
        patched_code=patched_1,
        changed_lines=[2, 3, 4],
        function_name="divide",
        function_params=params_1,
        issue_description="ZeroDivisionError crashes the application",
        patch_description="Handle zero divisor with proper error message",
        max_iterations=500,
        timeout_seconds=60.0,
    )

    # Demo 2: Regression
    print()
    print("-" * 80)
    print("DEMO 2: Regression - Negative Index Support Removed")
    print("-" * 80)

    original_2 = """
def get_item(items, index):
    if index < 0:
        index = len(items) + index
    return items[index]
"""

    patched_2 = """
def get_item(items, index):
    if index < 0:
        raise IndexError("Negative indices not supported")
    return items[index]
"""

    params_2 = [
        {'name': 'items', 'type': 'list'},
        {'name': 'index', 'type': 'int'},
    ]

    print("Original: Supports negative indexing (items[-1] returns last element)")
    print("Patched:  Raises IndexError for negative indices")
    print()
    print("Expected behavior: Atheris should detect this as REGRESSION")
    print("                   (previously working inputs now fail)")
    print()

    result_2 = run_atheris_fuzzing(
        original_code=original_2,
        patched_code=patched_2,
        changed_lines=[3, 4],
        function_name="get_item",
        function_params=params_2,
        issue_description="",  # No issue - makes it suspicious
        patch_description="Simplify index handling",
        max_iterations=500,
        timeout_seconds=60.0,
    )

    # Demo 3: Edge case improvement
    print()
    print("-" * 80)
    print("DEMO 3: Edge Case - Empty List Handling")
    print("-" * 80)

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

    params_3 = [
        {'name': 'items', 'type': 'list'},
    ]

    print("Original: Crashes on empty list (IndexError)")
    print("Patched:  Returns None for empty list")
    print()
    print("Expected behavior: Atheris should find this is EXPECTED fix")
    print()

    result_3 = run_atheris_fuzzing(
        original_code=original_3,
        patched_code=patched_3,
        changed_lines=[2, 3, 4],
        function_name="first_element",
        function_params=params_3,
        issue_description="Function crashes on empty list, should return None",
        patch_description="Handle empty list edge case gracefully",
        max_iterations=500,
        timeout_seconds=60.0,
    )

    # Summary
    print()
    print("=" * 80)
    print("DEMO SUMMARY")
    print("=" * 80)
    print()
    print(f"Demo 1 (Bug Fix):    {result_1.verdict}")
    print(f"  - Expected divergences: {result_1.expected_divergences}")
    print(f"  - Regressions: {result_1.regressions}")
    print()
    print(f"Demo 2 (Regression): {result_2.verdict}")
    print(f"  - Expected divergences: {result_2.expected_divergences}")
    print(f"  - Regressions: {result_2.regressions}")
    print()
    print(f"Demo 3 (Edge Case):  {result_3.verdict}")
    print(f"  - Expected divergences: {result_3.expected_divergences}")
    print(f"  - Regressions: {result_3.regressions}")
    print()
    print("KEY INSIGHT: Coverage-guided fuzzing actively seeks inputs that")
    print("hit the CHANGED code, making it more effective at finding")
    print("behavioral differences than random testing.")

    return {
        'demo_1_bug_fix': result_1.to_dict(),
        'demo_2_regression': result_2.to_dict(),
        'demo_3_edge_case': result_3.to_dict(),
    }


def run_on_files(
    original_file: Path,
    patched_file: Path,
    function_name: str,
    params_json: str,
    changed_lines: List[int] = None,
    class_name: str = None,
    issue_desc: str = "",
    patch_desc: str = "",
    max_iterations: int = 10000,
    timeout: float = 300.0,
    output_json: Path = None,
):
    """Run fuzzing on actual code files."""
    original_code = original_file.read_text()
    patched_code = patched_file.read_text()

    # Parse params
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON for params: {params_json}")
        sys.exit(1)

    # If changed_lines not provided, assume all lines changed
    if not changed_lines:
        changed_lines = list(range(1, len(patched_code.splitlines()) + 1))
        print(f"Warning: No changed_lines provided, using all {len(changed_lines)} lines")

    result = run_atheris_fuzzing(
        original_code=original_code,
        patched_code=patched_code,
        changed_lines=changed_lines,
        function_name=function_name,
        function_params=params,
        class_name=class_name,
        issue_description=issue_desc,
        patch_description=patch_desc,
        max_iterations=max_iterations,
        timeout_seconds=timeout,
    )

    if output_json:
        output_json.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"\nResults saved to: {output_json}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Atheris-based coverage-guided differential fuzzing"
    )

    parser.add_argument("--demo", action="store_true",
                       help="Run demonstration with example patches")

    parser.add_argument("--original-file", type=Path,
                       help="Path to original (pre-patch) code file")
    parser.add_argument("--patched-file", type=Path,
                       help="Path to patched code file")
    parser.add_argument("--function-name", type=str,
                       help="Name of function to fuzz")
    parser.add_argument("--params", type=str, default="[]",
                       help='JSON array of params: [{"name": "x", "type": "int"}, ...]')
    parser.add_argument("--changed-lines", type=str, default="",
                       help="Comma-separated list of changed line numbers")
    parser.add_argument("--class-name", type=str,
                       help="Class name if testing a method")
    parser.add_argument("--issue-description", type=str, default="",
                       help="GitHub issue description (for classification)")
    parser.add_argument("--patch-description", type=str, default="",
                       help="Commit message (for classification)")
    parser.add_argument("--max-iterations", type=int, default=10000,
                       help="Maximum fuzzing iterations")
    parser.add_argument("--timeout", type=float, default=300.0,
                       help="Fuzzing timeout in seconds")
    parser.add_argument("--output-json", type=Path,
                       help="Output results to JSON file")

    args = parser.parse_args()

    if args.demo:
        results = run_demo()
        if args.output_json:
            args.output_json.write_text(json.dumps(results, indent=2))
        return

    if not all([args.original_file, args.patched_file, args.function_name]):
        print("Error: --original-file, --patched-file, and --function-name required")
        print("       Or use --demo for demonstration")
        parser.print_help()
        sys.exit(1)

    # Parse changed lines
    changed_lines = None
    if args.changed_lines:
        changed_lines = [int(x.strip()) for x in args.changed_lines.split(",")]

    result = run_on_files(
        original_file=args.original_file,
        patched_file=args.patched_file,
        function_name=args.function_name,
        params_json=args.params,
        changed_lines=changed_lines,
        class_name=args.class_name,
        issue_desc=args.issue_description,
        patch_desc=args.patch_description,
        max_iterations=args.max_iterations,
        timeout=args.timeout,
        output_json=args.output_json,
    )

    # Exit code based on verdict
    if result.verdict == "FAIL":
        sys.exit(1)
    elif result.verdict == "WARNING":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
