#!/usr/bin/env python3
"""
Merge and summarize results from SLURM array job.

Usage:
    python merge_array_results.py <array_job_id>
    python merge_array_results.py <array_job_id> --output summary.json
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


def merge_array_results(job_id: str, output_file: str = None) -> Dict[str, Any]:
    """
    Merge results from SLURM array job and create summary.

    Args:
        job_id: SLURM array job ID
        output_file: Optional path to save combined results

    Returns:
        Summary dictionary with statistics
    """
    harness_dir = Path("/fs/nexus-scratch/ihbas/verifier_harness")
    results_dir = harness_dir / "results" / f"array_{job_id}"

    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        return None

    # Collect all result files
    result_files = sorted(results_dir.glob("*.json"))

    print(f"📊 Found {len(result_files)} result files in {results_dir}")
    print()

    # Load all results
    results = []
    failed_to_load = []

    for result_file in result_files:
        try:
            with open(result_file) as f:
                result = json.load(f)
                results.append(result)
        except Exception as e:
            print(f"⚠️  Failed to load {result_file.name}: {e}")
            failed_to_load.append(result_file.name)

    print(f"✅ Successfully loaded {len(results)} results")
    if failed_to_load:
        print(f"⚠️  Failed to load {len(failed_to_load)} files")
    print()

    # Create summary statistics
    summary = {
        "job_id": job_id,
        "total_instances": len(results),
        "verdicts": defaultdict(int),
        "swebench_stats": {"passed": 0, "failed": 0, "error": 0, "skipped": 0},
        "fuzzing_stats": {"passed": 0, "failed": 0, "error": 0, "skipped": 0},
        "failed_instances": [],
        "passed_instances": [],
    }

    for result in results:
        instance_id = result.get("instance_id", "unknown")
        verdict = result.get("overall_verdict", "UNKNOWN")

        # Count verdicts
        summary["verdicts"][verdict] += 1

        # Track passed/failed instances
        if verdict.startswith("PASS"):
            summary["passed_instances"].append(instance_id)
        elif verdict.startswith("FAIL") or verdict == "ERROR":
            summary["failed_instances"].append(instance_id)

        # SWE-bench stats
        swebench = result.get("swebench")
        if swebench:
            if swebench.get("success"):
                summary["swebench_stats"]["passed"] += 1
            elif swebench.get("error"):
                summary["swebench_stats"]["error"] += 1
            else:
                summary["swebench_stats"]["failed"] += 1
        else:
            summary["swebench_stats"]["skipped"] += 1

        # Fuzzing stats
        fuzzing = result.get("fuzzing")
        if fuzzing:
            if fuzzing.get("success"):
                summary["fuzzing_stats"]["passed"] += 1
            elif fuzzing.get("error"):
                summary["fuzzing_stats"]["error"] += 1
            else:
                summary["fuzzing_stats"]["failed"] += 1
        else:
            summary["fuzzing_stats"]["skipped"] += 1

    # Convert defaultdict to regular dict
    summary["verdicts"] = dict(summary["verdicts"])

    # Print summary
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total instances: {summary['total_instances']}")
    print()
    print("Overall Verdicts:")
    for verdict, count in sorted(summary["verdicts"].items()):
        pct = (count / summary['total_instances']) * 100 if summary['total_instances'] > 0 else 0
        print(f"  {verdict}: {count} ({pct:.1f}%)")
    print()
    print("SWE-bench Tests:")
    print(f"  Passed:  {summary['swebench_stats']['passed']}")
    print(f"  Failed:  {summary['swebench_stats']['failed']}")
    print(f"  Error:   {summary['swebench_stats']['error']}")
    print(f"  Skipped: {summary['swebench_stats']['skipped']}")
    print()
    print("Fuzzing Tests:")
    print(f"  Passed:  {summary['fuzzing_stats']['passed']}")
    print(f"  Failed:  {summary['fuzzing_stats']['failed']}")
    print(f"  Error:   {summary['fuzzing_stats']['error']}")
    print(f"  Skipped: {summary['fuzzing_stats']['skipped']}")
    print("=" * 70)

    # Save combined results if requested
    if output_file:
        output_path = Path(output_file)
        combined = {
            "summary": summary,
            "results": results
        }

        with open(output_path, 'w') as f:
            json.dump(combined, f, indent=2)

        print(f"\n💾 Combined results saved to: {output_path}")

    # Save summary separately
    summary_path = results_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"💾 Summary saved to: {summary_path}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge and summarize results from SLURM array job"
    )
    parser.add_argument(
        "job_id",
        help="SLURM array job ID (e.g., 6092095)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Optional: Save combined results to file (warning: can be large)"
    )

    args = parser.parse_args()

    merge_array_results(args.job_id, args.output)
