#!/usr/bin/env python3
"""
Extract the best instances from scored_issues.json for testing the agentic hybrid loop.
"""
import json
from typing import List, Dict, Any


def load_scored_issues(filepath: str) -> Dict[str, Any]:
    """Load the scored issues JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def filter_instances(
    issues: List[Dict[str, Any]],
    min_score: int = 70,
    tiers: List[int] = [1],
    min_testability: str = "high",
    max_patch_lines: int = None,
    max_files_modified: int = None,
    repos: List[str] = None,
    require_code_examples: bool = True
) -> List[Dict[str, Any]]:
    """
    Filter instances based on criteria.

    Args:
        issues: List of issue dictionaries
        min_score: Minimum score threshold (0-100)
        tiers: List of acceptable tiers (1, 2, or 3)
        min_testability: Minimum testability level ("high", "medium", "low")
        max_patch_lines: Maximum patch lines (None for no limit)
        max_files_modified: Maximum files modified (None for no limit)
        repos: List of specific repos to include (None for all)
        require_code_examples: Whether to require code examples

    Returns:
        Filtered list of issues
    """
    testability_order = {"low": 0, "medium": 1, "high": 2}
    min_test_level = testability_order.get(min_testability, 2)

    filtered = []
    for issue in issues:
        # Check score
        if issue["score"] < min_score:
            continue

        # Check tier
        if issue["tier"] not in tiers:
            continue

        # Check testability
        if testability_order.get(issue["testability"], 0) < min_test_level:
            continue

        # Check patch lines
        if max_patch_lines is not None and issue["patch_lines"] > max_patch_lines:
            continue

        # Check files modified
        if max_files_modified is not None and issue["files_modified"] > max_files_modified:
            continue

        # Check repos
        if repos is not None and issue["repo"] not in repos:
            continue

        # Check code examples
        if require_code_examples and not issue["has_code_examples"]:
            continue

        filtered.append(issue)

    return filtered


def print_instances_summary(issues: List[Dict[str, Any]]):
    """Print a summary of selected instances."""
    print(f"\n{'='*80}")
    print(f"SELECTED INSTANCES: {len(issues)}")
    print(f"{'='*80}\n")

    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue['instance_id']}")
        print(f"   Repo: {issue['repo']}")
        print(f"   Score: {issue['score']} | Tier: {issue['tier']} | Testability: {issue['testability']}")
        print(f"   Patch: {issue['patch_lines']} lines, {issue['files_modified']} files")
        print(f"   Code examples: {issue['has_code_examples']} | Exception mention: {issue['has_exception_mention']}")
        print()


def export_instance_ids(issues: List[Dict[str, Any]], output_file: str):
    """Export just the instance IDs to a file."""
    instance_ids = [issue["instance_id"] for issue in issues]

    with open(output_file, 'w') as f:
        json.dump(instance_ids, f, indent=2)

    print(f"✓ Exported {len(instance_ids)} instance IDs to {output_file}")


def export_full_instances(issues: List[Dict[str, Any]], output_file: str):
    """Export full instance data to a file."""
    with open(output_file, 'w') as f:
        json.dump(issues, f, indent=2)

    print(f"✓ Exported {len(issues)} full instances to {output_file}")


def main():
    # Load data
    input_file = "/fs/nexus-scratch/ihbas/verifier_harness/swe_bench_analysis/scored_issues.json"
    data = load_scored_issues(input_file)

    print(f"Loaded {data['metadata']['total_scored']} scored issues")

    # Example 1: Get top-tier instances with high scores
    print("\n" + "="*80)
    print("OPTION 1: Top-tier instances (Tier 1, Score >= 80)")
    print("="*80)
    best_instances = filter_instances(
        data["issues"],
        min_score=80,
        tiers=[1],
        min_testability="high",
        require_code_examples=True
    )
    print(f"Found {len(best_instances)} instances")
    print_instances_summary(best_instances[:10])  # Show first 10

    # Example 2: Small patches only (easier to verify)
    print("\n" + "="*80)
    print("OPTION 2: Small patches (≤10 lines, 1-2 files)")
    print("="*80)
    small_patches = filter_instances(
        data["issues"],
        min_score=70,
        tiers=[1, 2],
        max_patch_lines=10,
        max_files_modified=2,
        min_testability="high",
        require_code_examples=True
    )
    print(f"Found {len(small_patches)} instances")
    print_instances_summary(small_patches[:10])

    # Example 3: Specific repos you've been working with
    print("\n" + "="*80)
    print("OPTION 3: Your current repos (astropy, psf/requests, pylint)")
    print("="*80)
    current_repos = filter_instances(
        data["issues"],
        min_score=70,
        tiers=[1],
        repos=["astropy/astropy", "psf/requests", "pylint-dev/pylint"],
        min_testability="high"
    )
    print(f"Found {len(current_repos)} instances")
    print_instances_summary(current_repos)

    # Export options
    print("\n" + "="*80)
    print("EXPORT OPTIONS")
    print("="*80)

    # Export just IDs for easy testing
    export_instance_ids(best_instances, "best_instances_ids.json")
    export_instance_ids(small_patches, "small_patch_instances_ids.json")
    export_instance_ids(current_repos, "current_repos_instances_ids.json")

    # Export full data
    export_full_instances(best_instances, "best_instances_full.json")

    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR AGENTIC HYBRID LOOP")
    print("="*80)
    print("1. Start with 'current_repos_instances_ids.json' - familiar repos")
    print("2. Then try 'small_patch_instances_ids.json' - easier to verify")
    print("3. Finally 'best_instances_ids.json' - highest quality overall")


if __name__ == "__main__":
    main()
