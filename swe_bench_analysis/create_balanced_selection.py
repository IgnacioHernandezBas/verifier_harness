#!/usr/bin/env python3
"""
Create balanced instance selection for thesis.

This script:
1. Loads your top50.json
2. Adds Tier 2 and Tier 3 instances by adjusting thresholds
3. Ensures repo diversity (max 25% per repo)
4. Outputs a balanced 35-instance set

Usage:
    python create_balanced_selection.py
"""

import json
from collections import defaultdict
from pathlib import Path

def load_top50():
    """Load your existing top50.json"""
    with open('top50.json', 'r') as f:
        data = json.load(f)
    return data['issues']


def reclassify_tiers(issues):
    """
    Reclassify tiers with more stringent thresholds.

    Old: Tier 1 >= 70, Tier 2 >= 50
    New: Tier 1 >= 80, Tier 2 >= 60
    """
    for issue in issues:
        score = issue['score']
        if score >= 80:
            issue['tier'] = 1
        elif score >= 60:
            issue['tier'] = 2
        else:
            issue['tier'] = 3
    return issues


def balanced_selection(issues, target_total=35):
    """
    Select instances with controlled diversity.

    Target distribution:
    - Tier 1: ~20 instances (57%)
    - Tier 2: ~10 instances (29%)
    - Tier 3: ~5 instances (14%)

    Repo diversity: max 25% from any single repo
    """

    # Separate by tier
    by_tier = {1: [], 2: [], 3: []}
    for issue in issues:
        by_tier[issue['tier']].append(issue)

    # Sort each tier by score (descending)
    for tier in by_tier:
        by_tier[tier].sort(key=lambda x: -x['score'])

    # Targets
    target_tier1 = 20
    target_tier2 = 10
    target_tier3 = 5
    max_per_repo = target_total // 4  # 8-9 instances max

    selected = []
    repo_counts = defaultdict(int)

    # Helper to select from a tier
    def select_from_tier(tier_issues, target):
        tier_selected = []
        for issue in tier_issues:
            if len(tier_selected) >= target:
                break
            if repo_counts[issue['repo']] >= max_per_repo:
                continue
            tier_selected.append(issue)
            repo_counts[issue['repo']] += 1
        return tier_selected

    # Select from each tier
    tier1_selected = select_from_tier(by_tier[1], target_tier1)
    tier2_selected = select_from_tier(by_tier[2], target_tier2)
    tier3_selected = select_from_tier(by_tier[3], target_tier3)

    selected = tier1_selected + tier2_selected + tier3_selected

    return selected, {
        'tier1': len(tier1_selected),
        'tier2': len(tier2_selected),
        'tier3': len(tier3_selected),
        'repo_counts': dict(repo_counts)
    }


def print_summary(selected, stats):
    """Print selection summary"""
    print("=" * 80)
    print("BALANCED INSTANCE SELECTION FOR THESIS")
    print("=" * 80)

    print(f"\nTotal instances: {len(selected)}")
    print(f"\nTier distribution:")
    print(f"  Tier 1 (easy):   {stats['tier1']:2d} instances ({stats['tier1']/len(selected)*100:.0f}%)")
    print(f"  Tier 2 (medium): {stats['tier2']:2d} instances ({stats['tier2']/len(selected)*100:.0f}%)")
    print(f"  Tier 3 (hard):   {stats['tier3']:2d} instances ({stats['tier3']/len(selected)*100:.0f}%)")

    print(f"\nRepo distribution:")
    for repo, count in sorted(stats['repo_counts'].items(), key=lambda x: -x[1]):
        pct = count / len(selected) * 100
        print(f"  {repo:35s} {count:2d} instances ({pct:.0f}%)")

    print("\n" + "=" * 80)
    print("SELECTED INSTANCES BY TIER")
    print("=" * 80)

    for tier_num in [1, 2, 3]:
        tier_name = {1: "EASY", 2: "MEDIUM", 3: "HARD"}[tier_num]
        tier_issues = [s for s in selected if s['tier'] == tier_num]

        if not tier_issues:
            continue

        print(f"\n{tier_name} (Tier {tier_num}) - {len(tier_issues)} instances:")
        print("-" * 80)

        for i, issue in enumerate(sorted(tier_issues, key=lambda x: -x['score']), 1):
            print(f"{i:2d}. {issue['instance_id']:45s} | Score: {issue['score']:3d} | {issue['repo']}")


def main():
    # Load existing top50
    print("Loading top50.json...")
    issues = load_top50()
    print(f"Loaded {len(issues)} issues")

    # Reclassify with stricter thresholds
    print("\nReclassifying tiers with stricter thresholds...")
    print("  Old: Tier 1 >= 70, Tier 2 >= 50, Tier 3 < 50")
    print("  New: Tier 1 >= 80, Tier 2 >= 60, Tier 3 < 60")
    issues = reclassify_tiers(issues)

    # Check new distribution
    tier_counts = defaultdict(int)
    for issue in issues:
        tier_counts[issue['tier']] += 1
    print(f"\nNew tier distribution in top50:")
    print(f"  Tier 1: {tier_counts[1]} issues")
    print(f"  Tier 2: {tier_counts[2]} issues")
    print(f"  Tier 3: {tier_counts[3]} issues")

    # Balanced selection
    print("\nPerforming balanced selection...")
    selected, stats = balanced_selection(issues, target_total=35)

    # Print summary
    print_summary(selected, stats)

    # Save to file
    output = {
        'metadata': {
            'selection_method': 'balanced_stratified',
            'total_instances': len(selected),
            'tier_thresholds': {
                'tier1': '>=80',
                'tier2': '60-79',
                'tier3': '<60'
            },
            'diversity_constraints': {
                'max_per_repo': '25%',
                'target_tier1': 20,
                'target_tier2': 10,
                'target_tier3': 5
            }
        },
        'statistics': stats,
        'instances': [
            {
                'instance_id': s['instance_id'],
                'repo': s['repo'],
                'score': s['score'],
                'tier': s['tier'],
                'patch_lines': s['patch_lines'],
                'testability': s['testability']
            }
            for s in selected
        ]
    }

    output_file = 'thesis_instances_balanced.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Balanced selection saved to: {output_file}")

    # Create simple instance ID list for easy reference
    instance_ids = [s['instance_id'] for s in selected]
    with open('thesis_instance_ids.txt', 'w') as f:
        f.write('\n'.join(instance_ids))

    print(f"✅ Instance IDs saved to: thesis_instance_ids.txt")

    # Warning if we didn't meet targets
    if stats['tier2'] < 8:
        print("\n⚠️  WARNING: Not enough Tier 2 instances!")
        print("   You may need to score more instances from SWE-bench Lite")
        print("   Run: python score_issues.py --output all_scored.json")

    if stats['tier3'] < 3:
        print("\n⚠️  WARNING: Not enough Tier 3 instances!")
        print("   Consider lowering tier 3 threshold to < 70 or score all instances")


if __name__ == '__main__':
    main()
