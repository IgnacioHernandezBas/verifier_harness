#!/usr/bin/env python3
"""
Compare our verification results with official SWE-bench ground truth.

This validates that our pipeline produces correct results.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def load_ground_truth(experiment: str) -> dict:
    """Load official SWE-bench results."""
    gt_path = Path(f"/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite/{experiment}/results/results.json")

    if not gt_path.exists():
        print(f"❌ Ground truth not found: {gt_path}")
        sys.exit(1)

    with open(gt_path) as f:
        data = json.load(f)

    # Convert to dict keyed by instance_id
    gt_dict = {}
    for entry in data:
        instance_id = entry.get('instance_id')
        if instance_id:
            gt_dict[instance_id] = entry

    return gt_dict


def load_our_results(job_id: str) -> dict:
    """Load our verification results."""
    results_dir = Path(f"/fs/nexus-scratch/ihbas/verifier_harness/results/array_{job_id}")

    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        sys.exit(1)

    our_dict = {}
    for result_file in results_dir.glob("*.json"):
        with open(result_file) as f:
            result = json.load(f)
            instance_id = result.get('instance_id')
            if instance_id:
                our_dict[instance_id] = result

    return our_dict


def compare_results(ground_truth: dict, our_results: dict):
    """Compare our results with ground truth."""

    # Find instances in both
    common_instances = set(ground_truth.keys()) & set(our_results.keys())
    only_gt = set(ground_truth.keys()) - set(our_results.keys())
    only_ours = set(our_results.keys()) - set(ground_truth.keys())

    print("=" * 70)
    print("COMPARISON WITH GROUND TRUTH")
    print("=" * 70)
    print(f"Ground truth instances: {len(ground_truth)}")
    print(f"Our results instances: {len(our_results)}")
    print(f"Common instances: {len(common_instances)}")

    if only_gt:
        print(f"⚠️  Missing from our results: {len(only_gt)}")
    if only_ours:
        print(f"⚠️  Extra in our results: {len(only_ours)}")

    print()

    # Compare verdicts for common instances
    matches = 0
    mismatches = 0
    mismatch_details = []

    # Categorize mismatches
    categories = defaultdict(int)

    for instance_id in sorted(common_instances):
        gt_entry = ground_truth[instance_id]
        our_entry = our_results[instance_id]

        # Ground truth: check 'resolved' field (True/False)
        gt_resolved = gt_entry.get('resolved', False)

        # Our result: check if SWE-bench tests passed
        our_passed = our_entry.get('swebench', {}).get('success', False)
        our_exit_code = our_entry.get('swebench', {}).get('exit_code', -999)
        our_error = our_entry.get('swebench', {}).get('error', '')

        if gt_resolved == our_passed:
            matches += 1
        else:
            mismatches += 1

            # Categorize the mismatch
            if gt_resolved and not our_passed:
                if our_exit_code == -1 and 'Timeout' in str(our_error):
                    category = "GT_PASS_OUR_TIMEOUT"
                elif our_exit_code == -1:
                    category = "GT_PASS_OUR_ERROR"
                else:
                    category = "GT_PASS_OUR_FAIL"
            else:
                if our_exit_code == -1 and 'Timeout' in str(our_error):
                    category = "GT_FAIL_OUR_TIMEOUT"
                elif our_exit_code == -1:
                    category = "GT_FAIL_OUR_ERROR"
                else:
                    category = "GT_FAIL_OUR_PASS"

            categories[category] += 1

            mismatch_details.append({
                'instance_id': instance_id,
                'ground_truth': 'PASS' if gt_resolved else 'FAIL',
                'our_result': 'PASS' if our_passed else 'FAIL',
                'our_exit_code': our_exit_code,
                'our_error': our_error[:100] if our_error else None,
                'category': category
            })

    # Print summary
    print("=" * 70)
    print("VERDICT COMPARISON")
    print("=" * 70)
    print(f"✅ Matches: {matches} ({matches/len(common_instances)*100:.1f}%)")
    print(f"❌ Mismatches: {mismatches} ({mismatches/len(common_instances)*100:.1f}%)")
    print()

    if mismatches > 0:
        print("Mismatch Categories:")
        for category, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"  {category}: {count}")
        print()

        print("Sample Mismatches (first 10):")
        print("-" * 70)
        for detail in mismatch_details[:10]:
            print(f"Instance: {detail['instance_id']}")
            print(f"  Ground Truth: {detail['ground_truth']}")
            print(f"  Our Result:   {detail['our_result']} (exit: {detail['our_exit_code']})")
            print(f"  Category:     {detail['category']}")
            if detail['our_error']:
                print(f"  Error:        {detail['our_error']}")
            print()

    # Overall statistics
    print("=" * 70)
    print("DETAILED STATISTICS")
    print("=" * 70)

    # Ground truth stats
    gt_passed = sum(1 for e in ground_truth.values() if e.get('resolved', False))
    gt_failed = len(ground_truth) - gt_passed

    print(f"Ground Truth:")
    print(f"  Resolved:   {gt_passed} ({gt_passed/len(ground_truth)*100:.1f}%)")
    print(f"  Unresolved: {gt_failed} ({gt_failed/len(ground_truth)*100:.1f}%)")
    print()

    # Our stats
    our_passed = sum(1 for e in our_results.values() if e.get('swebench', {}).get('success', False))
    our_failed_tests = sum(1 for e in our_results.values()
                           if not e.get('swebench', {}).get('success', False)
                           and e.get('swebench', {}).get('exit_code', 0) > 0)
    our_errors = sum(1 for e in our_results.values()
                    if e.get('swebench', {}).get('exit_code', 0) == -1)

    print(f"Our Results:")
    print(f"  Passed:       {our_passed} ({our_passed/len(our_results)*100:.1f}%)")
    print(f"  Failed Tests: {our_failed_tests} ({our_failed_tests/len(our_results)*100:.1f}%)")
    print(f"  Errors:       {our_errors} ({our_errors/len(our_results)*100:.1f}%)")
    print()

    # Accuracy metric
    accuracy = matches / len(common_instances) * 100 if common_instances else 0
    print("=" * 70)
    print(f"PIPELINE ACCURACY: {accuracy:.1f}%")
    print("=" * 70)

    if accuracy >= 95:
        print("✅ Excellent! Pipeline is highly accurate.")
    elif accuracy >= 85:
        print("✓ Good! Some discrepancies to investigate (likely timeouts).")
    elif accuracy >= 70:
        print("⚠️  Moderate accuracy. Investigate mismatches.")
    else:
        print("❌ Low accuracy. Pipeline may have issues.")

    return {
        'matches': matches,
        'mismatches': mismatches,
        'accuracy': accuracy,
        'mismatch_details': mismatch_details
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare results with ground truth")
    parser.add_argument("job_id", help="SLURM array job ID")
    parser.add_argument("--experiment", default="20250911_isea_claude-3.5-sonnet-20241022")
    parser.add_argument("--save-mismatches", help="Save mismatch details to JSON file")

    args = parser.parse_args()

    print("Loading ground truth...")
    ground_truth = load_ground_truth(args.experiment)

    print("Loading our results...")
    our_results = load_our_results(args.job_id)

    print()
    comparison = compare_results(ground_truth, our_results)

    if args.save_mismatches and comparison['mismatch_details']:
        output_path = Path(args.save_mismatches)
        with open(output_path, 'w') as f:
            json.dump(comparison['mismatch_details'], f, indent=2)
        print(f"\n💾 Mismatch details saved to: {output_path}")
