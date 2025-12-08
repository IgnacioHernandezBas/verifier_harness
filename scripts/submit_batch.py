#!/usr/bin/env python3
"""
Helper script to prepare and submit SLURM batch jobs for SWE-bench analysis.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def create_instance_list(repo_filter=None, limit=10):
    """Create list of instance IDs to process."""
    from swebench_integration import DatasetLoader
    
    loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True, split="test")
    instance_ids = []
    
    for sample in loader.iter_samples(limit=limit, filter_repo=repo_filter):
        instance_id = sample.get('metadata', {}).get('instance_id')
        if instance_id:
            instance_ids.append(instance_id)
    
    return instance_ids

def main():
    parser = argparse.ArgumentParser(description="Submit SWE-bench batch jobs to SLURM")
    parser.add_argument("--repo", help="Filter by repository (e.g., 'scikit-learn/scikit-learn')")
    parser.add_argument("--limit", type=int, default=10, help="Number of instances to process")
    parser.add_argument("--mode", choices=["build", "analyze"], default="analyze",
                       help="Job mode: 'build' (containers only) or 'analyze' (full pipeline)")
    parser.add_argument("--max-parallel", type=int, default=5,
                       help="Maximum jobs running in parallel")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be submitted without actually submitting")
    
    args = parser.parse_args()
    
    # Create instance list
    print(f"Loading instances from SWE-bench (repo={args.repo}, limit={args.limit})...")
    instance_ids = create_instance_list(args.repo, args.limit)
    
    if not instance_ids:
        print("No instances found!")
        return 1
    
    print(f"Found {len(instance_ids)} instances:")
    for i, iid in enumerate(instance_ids, 1):
        print(f"  {i}. {iid}")
    
    # Write instance IDs to file
    instance_file = REPO_ROOT / "instance_ids.txt"
    with open(instance_file, 'w') as f:
        for iid in instance_ids:
            f.write(f"{iid}\n")
    
    print(f"\nWrote instance IDs to: {instance_file}")
    
    # Prepare SLURM submission
    script = f"slurm_batch_{args.mode}.sh"
    array_spec = f"1-{len(instance_ids)}%{args.max_parallel}"
    
    print(f"\nSLURM Job Configuration:")
    print(f"  Script: {script}")
    print(f"  Array: {array_spec} ({len(instance_ids)} jobs, max {args.max_parallel} parallel)")
    print(f"  Mode: {args.mode}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would execute:")
        print(f"  sbatch --array={array_spec} {script}")
        return 0
    
    # Submit job
    print("\nSubmitting job...")
    cmd = ["sbatch", f"--array={array_spec}", script]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Job submitted successfully!")
        print(result.stdout)
        
        # Extract job ID and show monitoring commands
        job_id = result.stdout.strip().split()[-1]
        print(f"\nMonitoring commands:")
        print(f"  squeue -u $USER              # View your jobs")
        print(f"  squeue -j {job_id}           # View this job array")
        print(f"  tail -f logs/{{build,analyze}}_*  # Watch logs")
        print(f"  ls results/                  # Check results")
    else:
        print(f"✗ Job submission failed:")
        print(result.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
