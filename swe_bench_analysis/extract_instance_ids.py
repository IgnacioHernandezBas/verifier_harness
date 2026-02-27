#!/usr/bin/env python3
"""
Extract instance IDs from SWE-bench JSON files.

Usage:
    # Extract from top50.json
    python extract_instance_ids.py top50.json

    # Extract and save to file
    python extract_instance_ids.py top50.json --output top50_ids.txt

    # Extract only specific tier
    python extract_instance_ids.py top50.json --tier 1

    # Extract only specific repo
    python extract_instance_ids.py top50.json --repo pytest

    # Get just the count
    python extract_instance_ids.py top50.json --count
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


def load_json(file_path: str) -> List[Dict[str, Any]]:
    """Load JSON file and extract issues list."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Handle different JSON structures
    if isinstance(data, list):
        return data
    elif 'issues' in data:
        return data['issues']
    elif 'instances' in data:
        return data['instances']
    else:
        raise ValueError(f"Unknown JSON structure. Expected 'issues' or 'instances' key.")


def extract_ids(
    issues: List[Dict[str, Any]],
    tier: int = None,
    repo: str = None,
    min_score: int = None,
    max_score: int = None
) -> List[str]:
    """Extract instance IDs with optional filters."""
    filtered = issues

    # Apply filters
    if tier is not None:
        filtered = [i for i in filtered if i.get('tier') == tier]

    if repo is not None:
        repo_lower = repo.lower()
        filtered = [i for i in filtered if repo_lower in i.get('repo', '').lower()]

    if min_score is not None:
        filtered = [i for i in filtered if i.get('score', 0) >= min_score]

    if max_score is not None:
        filtered = [i for i in filtered if i.get('score', 100) <= max_score]

    # Extract IDs
    return [issue.get('instance_id') for issue in filtered if issue.get('instance_id')]


def print_ids(ids: List[str], format: str = 'list'):
    """Print IDs in various formats."""
    if format == 'list':
        for id in ids:
            print(id)
    elif format == 'comma':
        print(','.join(ids))
    elif format == 'json':
        print(json.dumps(ids, indent=2))
    elif format == 'python':
        print('ids = [')
        for id in ids:
            print(f'    "{id}",')
        print(']')


def main():
    parser = argparse.ArgumentParser(
        description='Extract instance IDs from SWE-bench JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all IDs
  python extract_instance_ids.py top50.json

  # Save to file
  python extract_instance_ids.py top50.json -o ids.txt

  # Filter by tier
  python extract_instance_ids.py top50.json --tier 1

  # Filter by repo
  python extract_instance_ids.py top50.json --repo pytest

  # Filter by score range
  python extract_instance_ids.py top50.json --min-score 90

  # Output as comma-separated
  python extract_instance_ids.py top50.json --format comma

  # Output as Python list
  python extract_instance_ids.py top50.json --format python
        """
    )

    parser.add_argument('input_file', help='Input JSON file')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('-t', '--tier', type=int, choices=[1, 2, 3],
                       help='Filter by tier')
    parser.add_argument('-r', '--repo', help='Filter by repo (substring match)')
    parser.add_argument('--min-score', type=int, help='Minimum score')
    parser.add_argument('--max-score', type=int, help='Maximum score')
    parser.add_argument('-f', '--format', choices=['list', 'comma', 'json', 'python'],
                       default='list', help='Output format')
    parser.add_argument('-c', '--count', action='store_true',
                       help='Only print count')
    parser.add_argument('-s', '--stats', action='store_true',
                       help='Print statistics')

    args = parser.parse_args()

    # Load JSON
    try:
        issues = load_json(args.input_file)
    except Exception as e:
        print(f"Error loading {args.input_file}: {e}")
        return 1

    # Extract IDs
    ids = extract_ids(
        issues,
        tier=args.tier,
        repo=args.repo,
        min_score=args.min_score,
        max_score=args.max_score
    )

    # Print stats if requested
    if args.stats:
        print(f"Total instances: {len(issues)}")
        print(f"Filtered instances: {len(ids)}")

        # Repo breakdown
        from collections import defaultdict
        repo_counts = defaultdict(int)
        tier_counts = defaultdict(int)
        for issue in issues:
            if issue.get('instance_id') in ids:
                repo_counts[issue.get('repo')] += 1
                tier_counts[issue.get('tier')] += 1

        print("\nBy repo:")
        for repo, count in sorted(repo_counts.items(), key=lambda x: -x[1]):
            print(f"  {repo}: {count}")

        if tier_counts:
            print("\nBy tier:")
            for tier in sorted(tier_counts.keys()):
                print(f"  Tier {tier}: {tier_counts[tier]}")

        return 0

    # Print count only if requested
    if args.count:
        print(len(ids))
        return 0

    # Output IDs
    if args.output:
        with open(args.output, 'w') as f:
            if args.format == 'list':
                f.write('\n'.join(ids))
            elif args.format == 'comma':
                f.write(','.join(ids))
            elif args.format == 'json':
                f.write(json.dumps(ids, indent=2))
            elif args.format == 'python':
                f.write('ids = [\n')
                for id in ids:
                    f.write(f'    "{id}",\n')
                f.write(']\n')
        print(f"✅ {len(ids)} instance IDs saved to {args.output}")
    else:
        print_ids(ids, args.format)

    return 0


if __name__ == '__main__':
    exit(main())
