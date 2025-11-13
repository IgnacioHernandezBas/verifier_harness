#!/usr/bin/env python3
"""
Analyze SWE-bench repos to determine compatibility with PYTHONPATH approach.
"""

import sys
from pathlib import Path
from collections import Counter

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from swebench_integration.dataset_loader import DatasetLoader

def analyze_repos():
    """Analyze all repos in SWE-bench Verified."""

    loader = DatasetLoader(
        source="princeton-nlp/SWE-bench_Verified",
        hf_mode=True,
        split="test",
    )

    repo_counter = Counter()
    repo_samples = {}
    test_format_by_repo = {}

    print("="*80)
    print("Analyzing SWE-bench_Verified repositories...")
    print("="*80)

    for sample in loader.iter_samples():
        repo = sample.get("repo", "unknown")
        instance_id = sample.get("metadata", {}).get("instance_id", "unknown")

        repo_counter[repo] += 1

        # Store first sample for each repo
        if repo not in repo_samples:
            repo_samples[repo] = sample

            # Check test format
            fail_to_pass = sample.get("metadata", {}).get("FAIL_TO_PASS", [])
            if isinstance(fail_to_pass, str):
                import ast
                try:
                    fail_to_pass = ast.literal_eval(fail_to_pass)
                except:
                    fail_to_pass = []

            if fail_to_pass and len(fail_to_pass) > 0:
                first_test = fail_to_pass[0]
                # Check if test has file path (contains '/')
                has_path = '/' in first_test or '::' in first_test
                test_format_by_repo[repo] = {
                    'has_full_path': has_path,
                    'example_test': first_test,
                    'instance_id': instance_id,
                }

    # Sort repos by count
    sorted_repos = repo_counter.most_common()

    print(f"\nTotal repositories: {len(sorted_repos)}")
    print(f"Total instances: {sum(repo_counter.values())}")
    print("\n" + "="*80)
    print("Repository Statistics:")
    print("="*80)

    for repo, count in sorted_repos:
        test_info = test_format_by_repo.get(repo, {})
        has_path = test_info.get('has_full_path', False)
        example = test_info.get('example_test', 'N/A')
        status = "✅ GOOD" if has_path else "⚠️  NEEDS PATH"

        print(f"\n{repo}")
        print(f"  Instances: {count}")
        print(f"  Test format: {status}")
        print(f"  Example test: {example[:80]}")

    # Summary
    print("\n" + "="*80)
    print("Compatibility Summary:")
    print("="*80)

    good_repos = [r for r, info in test_format_by_repo.items() if info.get('has_full_path', False)]
    needs_work = [r for r, info in test_format_by_repo.items() if not info.get('has_full_path', False)]

    print(f"\n✅ Repos with full test paths (READY): {len(good_repos)}")
    for repo in sorted(good_repos):
        count = repo_counter[repo]
        print(f"   - {repo} ({count} instances)")

    print(f"\n⚠️  Repos needing test path detection ({len(needs_work)}):")
    for repo in sorted(needs_work):
        count = repo_counter[repo]
        print(f"   - {repo} ({count} instances)")

    # Check for common Python package patterns
    print("\n" + "="*80)
    print("Package Installation Complexity (estimated):")
    print("="*80)

    simple_repos = []
    complex_repos = []

    for repo in sorted_repos:
        repo_name = repo[0]
        # Simple heuristic: scientific packages tend to be more complex
        if any(x in repo_name.lower() for x in ['astropy', 'scipy', 'numpy', 'pandas', 'sklearn']):
            complex_repos.append(repo_name)
        else:
            simple_repos.append(repo_name)

    print(f"\n🟢 Likely simple (pure Python): {len(simple_repos)}")
    for repo in simple_repos[:10]:  # Show first 10
        print(f"   - {repo}")
    if len(simple_repos) > 10:
        print(f"   ... and {len(simple_repos) - 10} more")

    print(f"\n🟡 Likely complex (may need build deps): {len(complex_repos)}")
    for repo in complex_repos:
        print(f"   - {repo}")

if __name__ == "__main__":
    analyze_repos()
