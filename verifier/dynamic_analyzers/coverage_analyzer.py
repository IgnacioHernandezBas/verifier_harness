"""
Analyze coverage focusing only on changed lines.

This is the KEY INNOVATION: traditional coverage measures the entire codebase,
but we only care about coverage of the lines that actually changed in the patch.

This makes fuzzing much faster and more targeted.
"""

from typing import Dict, List, Set, Any


class CoverageAnalyzer:
    """
    Calculate coverage for changed lines only.
    This is the key innovation: we don't care about unchanged code.
    """

    def calculate_changed_line_coverage(
        self,
        coverage_data: Dict,
        changed_lines: Dict[str, List[int]],
        all_changed_lines: List[int] = None
    ) -> Dict:
        """
        Calculate what percentage of changed lines are covered by tests.

        Args:
            coverage_data: coverage.py JSON output
            changed_lines: {function_name: [line_numbers]} from patch analysis
            all_changed_lines: Optional flat list of all changed lines

        Returns:
            {
                'overall_coverage': float (0.0 to 1.0),
                'per_function_coverage': {func: float},
                'uncovered_lines': [line_numbers],
                'covered_lines': [line_numbers],
                'total_changed_lines': int,
                'total_covered_lines': int
            }
        """
        if not coverage_data or 'files' not in coverage_data:
            # No coverage data available
            all_lines = all_changed_lines or []
            if not all_lines:
                for lines in changed_lines.values():
                    all_lines.extend(lines)

            return {
                'overall_coverage': 0.0,
                'per_function_coverage': {},
                'uncovered_lines': sorted(set(all_lines)),
                'covered_lines': [],
                'total_changed_lines': len(set(all_lines)),
                'total_covered_lines': 0
            }

        # Collect all changed lines
        all_changed_lines_set = set()
        if all_changed_lines:
            all_changed_lines_set.update(all_changed_lines)
        for lines in changed_lines.values():
            all_changed_lines_set.update(lines)

        # Collect all covered lines from coverage report
        covered_lines_all = set()
        missing_lines_all = set()

        for file_path, file_data in coverage_data.get('files', {}).items():
            # Get executed lines
            executed = file_data.get('executed_lines', [])
            covered_lines_all.update(executed)

            # Get missing lines
            missing = file_data.get('missing_lines', [])
            missing_lines_all.update(missing)

        # Find intersection: which changed lines were covered?
        covered_changed = all_changed_lines_set & covered_lines_all
        uncovered_changed = all_changed_lines_set - covered_lines_all

        # Calculate overall coverage
        overall_coverage = (
            len(covered_changed) / len(all_changed_lines_set)
            if all_changed_lines_set else 1.0
        )

        # Calculate per-function coverage
        per_function = {}
        for func_name, func_lines in changed_lines.items():
            func_lines_set = set(func_lines)
            covered_in_func = func_lines_set & covered_lines_all
            per_function[func_name] = (
                len(covered_in_func) / len(func_lines_set)
                if func_lines_set else 1.0
            )

        return {
            'overall_coverage': overall_coverage,
            'per_function_coverage': per_function,
            'uncovered_lines': sorted(uncovered_changed),
            'covered_lines': sorted(covered_changed),
            'total_changed_lines': len(all_changed_lines_set),
            'total_covered_lines': len(covered_changed)
        }

    def calculate_coverage_improvement(
        self,
        before_coverage: Dict,
        after_coverage: Dict
    ) -> Dict:
        """
        Calculate how much coverage improved after fuzzing.

        Args:
            before_coverage: Coverage before fuzzing
            after_coverage: Coverage after fuzzing

        Returns:
            {
                'coverage_delta': float,
                'newly_covered_lines': [line_numbers],
                'still_uncovered_lines': [line_numbers]
            }
        """
        before_cov = before_coverage.get('overall_coverage', 0.0)
        after_cov = after_coverage.get('overall_coverage', 0.0)

        before_covered = set(before_coverage.get('covered_lines', []))
        after_covered = set(after_coverage.get('covered_lines', []))

        newly_covered = after_covered - before_covered
        still_uncovered = set(after_coverage.get('uncovered_lines', []))

        return {
            'coverage_delta': after_cov - before_cov,
            'newly_covered_lines': sorted(newly_covered),
            'still_uncovered_lines': sorted(still_uncovered),
            'improvement_pct': (after_cov - before_cov) * 100
        }

    def generate_coverage_report(
        self,
        coverage_result: Dict,
        patch_analysis: Any
    ) -> str:
        """
        Generate a human-readable coverage report.

        Args:
            coverage_result: Result from calculate_changed_line_coverage
            patch_analysis: PatchAnalysis object

        Returns:
            Formatted string report
        """
        lines = [
            "=" * 80,
            "CHANGE-AWARE COVERAGE REPORT",
            "=" * 80,
            "",
            f"Changed Functions: {', '.join(patch_analysis.changed_functions) if patch_analysis.changed_functions else 'None'}",
            f"Total Changed Lines: {coverage_result['total_changed_lines']}",
            f"Covered Changed Lines: {coverage_result['total_covered_lines']}",
            f"Overall Coverage: {coverage_result['overall_coverage']:.1%}",
            "",
        ]

        # Per-function breakdown
        if coverage_result['per_function_coverage']:
            lines.append("Per-Function Coverage:")
            lines.append("-" * 40)
            for func, cov in coverage_result['per_function_coverage'].items():
                status = "✓" if cov >= 0.8 else "⚠" if cov >= 0.5 else "✗"
                lines.append(f"  {status} {func}: {cov:.1%}")
            lines.append("")

        # Uncovered lines
        if coverage_result['uncovered_lines']:
            lines.append(f"Uncovered Lines ({len(coverage_result['uncovered_lines'])}):")
            lines.append("-" * 40)
            uncov_lines = coverage_result['uncovered_lines']
            if len(uncov_lines) <= 20:
                lines.append(f"  {uncov_lines}")
            else:
                lines.append(f"  {uncov_lines[:20]}... (and {len(uncov_lines) - 20} more)")
            lines.append("")

        # Covered lines
        if coverage_result['covered_lines']:
            lines.append(f"Covered Lines ({len(coverage_result['covered_lines'])}):")
            lines.append("-" * 40)
            cov_lines = coverage_result['covered_lines']
            if len(cov_lines) <= 20:
                lines.append(f"  {cov_lines}")
            else:
                lines.append(f"  {cov_lines[:20]}... (and {len(cov_lines) - 20} more)")
            lines.append("")

        lines.append("=" * 80)

        return '\n'.join(lines)


# Example usage
if __name__ == "__main__":
    # Mock coverage data (from coverage.py JSON format)
    coverage_data = {
        'files': {
            'module_under_test.py': {
                'executed_lines': [1, 2, 3, 5, 6, 7],
                'missing_lines': [4, 8],
                'summary': {
                    'covered_lines': 6,
                    'num_statements': 8,
                    'percent_covered': 75.0
                }
            }
        },
        'totals': {
            'covered_lines': 6,
            'num_statements': 8,
            'percent_covered': 75.0
        }
    }

    # Changed lines from patch analysis
    changed_lines = {
        'divide': [3, 4, 5],
        'multiply': [7, 8]
    }
    all_changed_lines = [3, 4, 5, 7, 8]

    analyzer = CoverageAnalyzer()
    result = analyzer.calculate_changed_line_coverage(
        coverage_data,
        changed_lines,
        all_changed_lines
    )

    print("Coverage Analysis Result:")
    print(f"  Overall Coverage: {result['overall_coverage']:.1%}")
    print(f"  Total Changed Lines: {result['total_changed_lines']}")
    print(f"  Covered Lines: {result['covered_lines']}")
    print(f"  Uncovered Lines: {result['uncovered_lines']}")
    print(f"  Per-Function: {result['per_function_coverage']}")
