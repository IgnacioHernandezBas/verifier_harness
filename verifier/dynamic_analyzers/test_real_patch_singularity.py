#!/usr/bin/env python3
"""
Test script to verify patch application with a REAL SWE-bench instance using Singularity.
This uses actual data from princeton-nlp/SWE-bench_Verified.
"""

import json
import sys
import argparse
from pathlib import Path

# Add project root to path
CURRENT_DIR = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.test_patch_singularity import run_evaluation
from swebench_integration.dataset_loader import DatasetLoader


def main(
    dataset_source: str = "princeton-nlp/SWE-bench_Verified",
    split: str = "test",
    instance_id: str = None,
    repo_filter: str = None,
    limit: int = 1,
    image_path: str = "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
    force_rebuild: bool = False,
):
    """
    Fetch and test a real patch from SWE-bench using Singularity.

    Parameters:
    -----------
    dataset_source : str
        HuggingFace dataset name (e.g., "princeton-nlp/SWE-bench_Verified")
    split : str
        Dataset split to use (default: "test")
    instance_id : str
        Specific instance ID to test (optional)
    repo_filter : str
        Filter samples by repository name (optional)
    limit : int
        Number of samples to test (default: 1)
    image_path : str
        Path to Singularity image
    force_rebuild : bool
        Force rebuild of Singularity image
    """
    print("="*80)
    print(f"Fetching REAL SWE-bench patch from {dataset_source}")
    print(f"Using Singularity image: {image_path}")
    print("="*80)

    # Load dataset using DatasetLoader
    loader = DatasetLoader(
        source=dataset_source,
        hf_mode=True,
        split=split,
    )

    # Find the sample to test
    sample = None
    for s in loader.iter_samples(limit=100, filter_repo=repo_filter):
        # s contains: 'repo', 'base_commit', 'patch', 'problem_statement', 'metadata'
        instance_id_in_sample = s["metadata"].get("instance_id")

        # If instance_id specified, find that exact instance
        if instance_id and instance_id_in_sample == instance_id:
            sample = s
            break
        # Otherwise, take the first matching sample
        elif not instance_id:
            sample = s
            break

    if not sample:
        print(f"❌ No sample found matching criteria")
        if instance_id:
            print(f"   Instance ID: {instance_id}")
        if repo_filter:
            print(f"   Repo filter: {repo_filter}")
        sys.exit(1)

    print(f"\nInstance: {sample['metadata']['instance_id']}")
    print(f"Repo: {sample['repo']}")
    print(f"Base Commit: {sample['base_commit']}")

    # Get test information
    fail_to_pass = sample['metadata'].get('FAIL_TO_PASS', [])
    pass_to_pass = sample['metadata'].get('PASS_TO_PASS', [])

    # Handle string representations if needed
    if isinstance(fail_to_pass, str):
        import ast
        fail_to_pass = ast.literal_eval(fail_to_pass)
    if isinstance(pass_to_pass, str):
        import ast
        pass_to_pass = ast.literal_eval(pass_to_pass)

    print(f"\nFAIL_TO_PASS tests: {len(fail_to_pass)}")
    print(f"PASS_TO_PASS tests: {len(pass_to_pass)}")
    print(f"\nProblem statement:\n{sample.get('problem_statement', 'N/A')[:200]}...")

    # Create a prediction using the ACTUAL patch from the dataset
    # (this is the ground truth patch - should pass all tests)
    predictions = [
        {
            "instance_id": sample["metadata"]["instance_id"],
            "model_name_or_path": "ground-truth",
            "model_patch": sample["patch"],
        }
    ]

    print("\n" + "="*80)
    print("Running evaluation with Singularity...")
    print("="*80 + "\n")

    try:
        eval_results = run_evaluation(
            predictions=predictions,
            image_path=image_path,
            dataset_source=dataset_source,
            hf_mode=True,
            split=split,
            force_rebuild=force_rebuild,
        )
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "="*80)
    print("📊 Evaluation Results")
    print("="*80)
    print(json.dumps(eval_results, indent=2))

    # Check if it passed
    if eval_results and len(eval_results) > 0:
        result = eval_results[0]
        if result.get("passed"):
            print("\n✅ SUCCESS! Ground truth patch passed all tests!")
            sys.exit(0)
        else:
            print(f"\n❌ FAILED: {result.get('status', 'unknown')}")
            if 'error' in result:
                print(f"Error: {result['error']}")
            if 'stderr' in result:
                print(f"\nStderr:\n{result['stderr'][:500]}")
            sys.exit(1)
    else:
        print("\n❌ No results returned")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test a real patch from SWE-bench dataset using Singularity"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench_Verified",
        help="HuggingFace dataset name (default: princeton-nlp/SWE-bench_Verified)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split (default: test)",
    )
    parser.add_argument(
        "--instance-id",
        type=str,
        default=None,
        help="Specific instance ID to test (e.g., astropy__astropy-12907)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Filter by repository (e.g., astropy/astropy)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of samples to test (default: 1)",
    )
    parser.add_argument(
        "--image-path",
        type=str,
        default="/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
        help="Path to Singularity image",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild of Singularity image",
    )

    args = parser.parse_args()

    main(
        dataset_source=args.dataset,
        split=args.split,
        instance_id=args.instance_id,
        repo_filter=args.repo,
        limit=args.limit,
        image_path=args.image_path,
        force_rebuild=args.force_rebuild,
    )
