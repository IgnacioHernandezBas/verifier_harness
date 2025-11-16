#!/usr/bin/env python3
"""
Merge results from SLURM array job chunks into a single JSON file.

Usage:
    python merge_results.py --job-id 12345 --output final_results.json
    python merge_results.py --pattern "results/fuzzing_12345_task*.json" --output merged.json
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
import glob


def load_chunk_results(pattern: str) -> List[Dict[str, Any]]:
    """Load all result chunks matching the pattern"""
    chunk_files = sorted(glob.glob(pattern))

    if not chunk_files:
        raise FileNotFoundError(f"No result files found matching: {pattern}")

    print(f"Found {len(chunk_files)} result files:")
    for f in chunk_files:
        print(f"  - {f}")

    all_results = []
    for chunk_file in chunk_files:
        try:
            with open(chunk_file, 'r') as f:
                chunk_data = json.load(f)

            # Handle both list and dict formats
            if isinstance(chunk_data, list):
                all_results.extend(chunk_data)
            elif isinstance(chunk_data, dict) and 'results' in chunk_data:
                all_results.extend(chunk_data['results'])
            else:
                print(f"Warning: Unexpected format in {chunk_file}")
                all_results.append(chunk_data)

        except Exception as e:
            print(f"Error loading {chunk_file}: {e}")
            continue

    return all_results


def compute_summary_stats(results: List[Dict]) -> Dict[str, Any]:
    """Compute summary statistics from results"""
    total = len(results)

    if total == 0:
        return {'total': 0, 'error': 'No results to summarize'}

    verdicts = {}
    for result in results:
        verdict = result.get('verdict', 'UNKNOWN')
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

    # Calculate average times
    times = [r.get('execution_time', 0) for r in results if 'execution_time' in r]
    avg_time = sum(times) / len(times) if times else 0

    # Coverage stats
    coverages = []
    for result in results:
        if 'fuzzing_result' in result and 'coverage' in result['fuzzing_result']:
            cov = result['fuzzing_result']['coverage'].get('overall_coverage', 0)
            coverages.append(cov)

    avg_coverage = sum(coverages) / len(coverages) if coverages else 0

    return {
        'total_patches': total,
        'verdicts': verdicts,
        'accept_rate': verdicts.get('ACCEPT', 0) / total,
        'reject_rate': verdicts.get('REJECT', 0) / total,
        'warning_rate': verdicts.get('WARNING', 0) / total,
        'error_rate': verdicts.get('ERROR', 0) / total,
        'avg_execution_time': avg_time,
        'avg_coverage': avg_coverage,
        'coverage_measured': len(coverages)
    }


def main():
    parser = argparse.ArgumentParser(description='Merge SLURM array job results')
    parser.add_argument(
        '--job-id',
        help='SLURM array job ID (will look for results/fuzzing_JOBID_task*.json)'
    )
    parser.add_argument(
        '--pattern',
        help='Glob pattern for result files (e.g., "results/fuzzing_*_task*.json")'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output file for merged results'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print summary statistics'
    )

    args = parser.parse_args()

    # Determine file pattern
    if args.job_id:
        pattern = f"results/fuzzing_{args.job_id}_task*.json"
    elif args.pattern:
        pattern = args.pattern
    else:
        parser.error("Must specify either --job-id or --pattern")

    print(f"Loading results matching: {pattern}")
    print("=" * 60)

    # Load results
    try:
        results = load_chunk_results(pattern)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    print(f"\n✓ Loaded {len(results)} total results")

    # Compute summary
    summary = compute_summary_stats(results)

    # Prepare output
    output_data = {
        'summary': summary,
        'results': results
    }

    # Write merged file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Merged results saved to: {args.output}")

    # Print summary if requested
    if args.summary:
        print("\n" + "=" * 60)
        print("SUMMARY STATISTICS")
        print("=" * 60)
        print(f"Total patches: {summary['total_patches']}")
        print(f"\nVerdicts:")
        for verdict, count in summary['verdicts'].items():
            pct = count / summary['total_patches'] * 100
            print(f"  {verdict:10s}: {count:4d} ({pct:5.1f}%)")
        print(f"\nAverage execution time: {summary['avg_execution_time']:.2f}s")
        if summary['coverage_measured'] > 0:
            print(f"Average coverage: {summary['avg_coverage']:.1%}")
            print(f"Coverage measured for: {summary['coverage_measured']} patches")
        print("=" * 60)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
