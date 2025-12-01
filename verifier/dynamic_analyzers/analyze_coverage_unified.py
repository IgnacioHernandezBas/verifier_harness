"""
Unified coverage analysis helper for notebook.
Analyzes both line and branch coverage in one function.
"""

def analyze_coverage_unified(coverage_data, patch_analysis, analyzer, label="Coverage"):
    """
    Analyze both line and branch coverage together.

    Args:
        coverage_data: Coverage JSON data
        patch_analysis: Patch analysis object
        analyzer: CoverageAnalyzer instance
        label: Label for output (e.g., "BASELINE" or "FUZZING")

    Returns:
        dict with both line and branch coverage results
    """
    if not coverage_data or not patch_analysis:
        return None

    # Calculate line coverage
    line_result = analyzer.calculate_changed_line_coverage(
        coverage_data=coverage_data,
        changed_lines=patch_analysis.changed_lines,
        all_changed_lines=patch_analysis.all_changed_lines
    )

    # Calculate branch coverage
    branch_result = analyzer.calculate_branch_coverage(
        coverage_data=coverage_data,
        changed_lines=patch_analysis.all_changed_lines
    )

    # Print unified report
    print(f"\n📊 {label} COVERAGE:")
    print(f"   Line coverage: {line_result['overall_coverage']*100:.1f}%")
    print(f"   Covered lines: {line_result['covered_lines']}")
    print(f"   Uncovered lines: {line_result['uncovered_lines']}")

    # Only show branch coverage if there are actually branches
    if branch_result['total_branches'] > 0:
        print(f"\n   Branch coverage: {branch_result['coverage']*100:.1f}%")
        print(f"   Total branches: {branch_result['total_branches']}")
        print(f"   Covered branches: {branch_result['covered_branches']}")
        if branch_result['missing_branches']:
            print(f"   Missing branches: {len(branch_result['missing_branches'])}")
    else:
        print(f"\n   ℹ️  Branch coverage: N/A (no conditional branches in changed code)")

    return {
        'line_result': line_result,
        'branch_result': branch_result,
        'line_coverage': line_result['overall_coverage'],
        'branch_coverage': branch_result['branch_coverage'],
        'covered_lines': set(line_result['covered_lines']),
        'uncovered_lines': line_result['uncovered_lines'],
    }
