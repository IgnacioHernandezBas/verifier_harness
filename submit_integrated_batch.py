#!/usr/bin/env python3
"""
Smart batch submission for integrated pipeline.

Handles multi-repo testing with intelligent scheduling and storage management.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict
import json


def get_disk_space() -> float:
    """Get available disk space in GB."""
    result = subprocess.run(
        ['df', '/fs/nexus-scratch'],
        capture_output=True,
        text=True
    )

    lines = result.stdout.strip().split('\n')
    if len(lines) >= 2:
        parts = lines[1].split()
        available_gb = int(parts[3]) / (1024 * 1024)
        return available_gb

    return 0


def get_cache_size() -> float:
    """Get current cache size in GB."""
    result = subprocess.run(
        ['du', '-sh', '/fs/nexus-scratch/ihbas/.cache/swebench_singularity/'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        size_str = result.stdout.split()[0]
        if 'G' in size_str:
            return float(size_str.rstrip('G'))
        elif 'M' in size_str:
            return float(size_str.rstrip('M')) / 1024

    return 0


def load_instances(repo_filter: str = None, limit: int = None, instance_file: Path = None) -> List[str]:
    """Load instance IDs from dataset or file."""

    if instance_file and instance_file.exists():
        print(f"Loading instances from: {instance_file}")
        with open(instance_file) as f:
            instance_ids = [line.strip() for line in f if line.strip()]
        return instance_ids

    # Load from dataset
    sys.path.insert(0, str(Path(__file__).parent))
    from swebench_integration import DatasetLoader

    print(f"Loading instances from SWE-bench (repo={repo_filter}, limit={limit})...")

    loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True, split="test")
    instance_ids = []

    for sample in loader.iter_samples(limit=limit, filter_repo=repo_filter):
        instance_id = sample.get('metadata', {}).get('instance_id')
        if instance_id:
            instance_ids.append(instance_id)

    return instance_ids


def group_instances_by_repo(instance_ids: List[str]) -> Dict[str, List[str]]:
    """Group instances by repository."""
    repo_groups = {}

    for instance_id in instance_ids:
        # Extract repo from instance ID (e.g., "scikit-learn__scikit-learn-10297")
        parts = instance_id.split('__')
        if len(parts) >= 2:
            repo = parts[0]
        else:
            repo = 'unknown'

        if repo not in repo_groups:
            repo_groups[repo] = []
        repo_groups[repo].append(instance_id)

    return repo_groups


def estimate_container_count(instance_ids: List[str]) -> int:
    """
    Estimate number of unique containers needed.
    Each unique repo+version combination needs its own container.
    """
    # In practice, each instance typically has a unique container
    # Conservative estimate: assume 80% unique containers
    return int(len(instance_ids) * 0.8)


def check_storage_capacity(instance_ids: List[str]) -> tuple[bool, str]:
    """
    Check if there's enough storage for the batch.

    Returns:
        (can_proceed, message)
    """
    available_gb = get_disk_space()
    cache_gb = get_cache_size()

    estimated_containers = estimate_container_count(instance_ids)
    estimated_size_gb = estimated_containers * 1.2  # 1.2 GB per container

    # Need some buffer space (5 GB)
    required_gb = estimated_size_gb + 5

    print("\n" + "="*70)
    print("Storage Check")
    print("="*70)
    print(f"Available disk space: {available_gb:.1f} GB")
    print(f"Current cache size: {cache_gb:.1f} GB")
    print(f"Instances to process: {len(instance_ids)}")
    print(f"Estimated new containers: {estimated_containers}")
    print(f"Estimated storage needed: {estimated_size_gb:.1f} GB")
    print(f"Total required (with buffer): {required_gb:.1f} GB")

    if available_gb < required_gb:
        message = (
            f"⚠️  WARNING: May not have enough disk space!\n"
            f"   Available: {available_gb:.1f} GB, Need: {required_gb:.1f} GB\n"
            f"   Consider:\n"
            f"   1. Reducing batch size (--limit)\n"
            f"   2. Cleaning up cache: python slurm_cleanup_cache.py --keep-recent 10\n"
            f"   3. Processing in smaller batches"
        )
        return False, message
    elif available_gb < required_gb * 1.5:
        message = (
            f"⚠️  CAUTION: Disk space is tight.\n"
            f"   Available: {available_gb:.1f} GB, Need: {required_gb:.1f} GB"
        )
        return True, message
    else:
        message = f"✓ Sufficient disk space ({available_gb:.1f} GB available)"
        return True, message


def submit_batch(
    instance_ids: List[str],
    max_parallel: int,
    enable_static: bool,
    enable_fuzzing: bool,
    enable_rules: bool,
    dry_run: bool = False
) -> int:
    """Submit SLURM batch job."""

    # Write instance IDs to file
    instance_file = Path("instance_ids.txt")
    with open(instance_file, 'w') as f:
        for iid in instance_ids:
            f.write(f"{iid}\n")

    print(f"\n✓ Wrote {len(instance_ids)} instance IDs to: {instance_file}")

    # Show repo breakdown
    repo_groups = group_instances_by_repo(instance_ids)
    print(f"\nInstances by repository:")
    for repo, instances in sorted(repo_groups.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {repo}: {len(instances)} instances")

    # Prepare SLURM submission
    array_spec = f"1-{len(instance_ids)}%{max_parallel}"
    script = "slurm_integrated_pipeline.sh"

    # Build sbatch command
    cmd = ["sbatch", f"--array={array_spec}", script]

    print(f"\n" + "="*70)
    print("SLURM Job Configuration")
    print("="*70)
    print(f"Script: {script}")
    print(f"Array: {array_spec}")
    print(f"  Total jobs: {len(instance_ids)}")
    print(f"  Max parallel: {max_parallel}")
    print(f"\nAnalysis Modules:")
    print(f"  Static: {'✅' if enable_static else '❌'}")
    print(f"  Fuzzing: {'✅' if enable_fuzzing else '❌'}")
    print(f"  Rules: {'✅' if enable_rules else '❌'}")

    if dry_run:
        print(f"\n[DRY RUN] Would execute:")
        print(f"  {' '.join(cmd)}")
        return 0

    # Submit job
    print(f"\nSubmitting job...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✓ Job submitted successfully!")
        print(result.stdout)

        # Extract job ID
        job_id = result.stdout.strip().split()[-1]

        print(f"\n" + "="*70)
        print("Monitoring Commands")
        print("="*70)
        print(f"View jobs:        squeue -u $USER")
        print(f"View this array:  squeue -j {job_id}")
        print(f"Watch logs:       tail -f logs/pipeline_*.out")
        print(f"Check results:    ls -lh results/")
        print(f"Cache status:     python slurm_cleanup_cache.py --status")

        print(f"\n" + "="*70)
        print("Cleanup Commands (if running low on space)")
        print("="*70)
        print(f"Keep 10 recent:   python slurm_cleanup_cache.py --keep-recent 10")
        print(f"Remove old (30d): python slurm_cleanup_cache.py --cleanup-age 30")
        print(f"Free to 15 GB:    python slurm_cleanup_cache.py --free-space 15")

    else:
        print(f"✗ Job submission failed:")
        print(result.stderr)
        return 1

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Submit integrated pipeline batch jobs with smart storage management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test 10 scikit-learn instances
  python submit_integrated_batch.py --repo "scikit-learn/scikit-learn" --limit 10 --max-parallel 3

  # Process multiple repos, 50 instances total
  python submit_integrated_batch.py --limit 50 --max-parallel 5

  # Use instance list from file
  python submit_integrated_batch.py --instance-file my_instances.txt --max-parallel 4

  # Check storage before submitting
  python submit_integrated_batch.py --repo "django/django" --limit 20 --dry-run
        """
    )

    # Input options
    parser.add_argument(
        '--repo',
        help='Filter by repository (e.g., "scikit-learn/scikit-learn")'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of instances to process'
    )

    parser.add_argument(
        '--instance-file',
        type=Path,
        help='File containing instance IDs (one per line)'
    )

    # Execution options
    parser.add_argument(
        '--max-parallel',
        type=int,
        default=5,
        help='Maximum parallel jobs (default: 5)'
    )

    # Analysis modules
    parser.add_argument(
        '--disable-static',
        action='store_true',
        help='Disable static analysis'
    )

    parser.add_argument(
        '--disable-fuzzing',
        action='store_true',
        help='Disable dynamic fuzzing'
    )

    parser.add_argument(
        '--disable-rules',
        action='store_true',
        help='Disable verification rules'
    )

    # Other options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be submitted without actually submitting'
    )

    parser.add_argument(
        '--skip-storage-check',
        action='store_true',
        help='Skip storage capacity check'
    )

    args = parser.parse_args()

    print("="*70)
    print("Integrated Pipeline - Smart Batch Submission")
    print("="*70)

    # Load instances
    try:
        instance_ids = load_instances(
            repo_filter=args.repo,
            limit=args.limit,
            instance_file=args.instance_file
        )
    except Exception as e:
        print(f"✗ Error loading instances: {e}")
        return 1

    if not instance_ids:
        print("✗ No instances found!")
        return 1

    print(f"✓ Loaded {len(instance_ids)} instances")

    # Check storage capacity
    if not args.skip_storage_check:
        can_proceed, message = check_storage_capacity(instance_ids)
        print(message)

        if not can_proceed and not args.dry_run:
            print("\nUse --skip-storage-check to override (not recommended)")
            return 1
    else:
        print("\n⚠️  Skipping storage check")

    # Submit batch
    return submit_batch(
        instance_ids=instance_ids,
        max_parallel=args.max_parallel,
        enable_static=not args.disable_static,
        enable_fuzzing=not args.disable_fuzzing,
        enable_rules=not args.disable_rules,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    sys.exit(main())
