#!/usr/bin/env python3
"""
Command-line interface for patch evaluation with dynamic fuzzing.

Usage:
    # Evaluate a single patch
    python scripts/eval_cli.py --patch-file patch.diff --code-file patched_code.py

    # Evaluate SWE-bench predictions
    python scripts/eval_cli.py --predictions predictions.json --dataset SWE-bench_Verified

    # Batch evaluation
    python scripts/eval_cli.py --batch patches/ --output results.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation_pipeline import EvaluationPipeline
from swebench_integration.dataset_loader import DatasetLoader


def load_patch_from_files(patch_file: str, code_file: str, patch_id: str = None) -> Dict[str, Any]:
    """Load patch data from separate files"""
    patch_path = Path(patch_file)
    code_path = Path(code_file)

    if not patch_path.exists():
        raise FileNotFoundError(f"Patch file not found: {patch_file}")
    if not code_path.exists():
        raise FileNotFoundError(f"Code file not found: {code_file}")

    diff = patch_path.read_text()
    patched_code = code_path.read_text()

    return {
        'id': patch_id or patch_path.stem,
        'diff': diff,
        'patched_code': patched_code
    }


def load_predictions(predictions_file: str) -> List[Dict[str, Any]]:
    """
    Load predictions from a JSON file.

    Expected format:
    [
        {
            "instance_id": "django__django-12345",
            "model_patch": "diff --git ...",
            "model_name_or_path": "gpt-4"
        },
        ...
    ]
    """
    predictions_path = Path(predictions_file)

    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {predictions_file}")

    with predictions_path.open('r') as f:
        predictions = json.load(f)

    return predictions


def evaluate_predictions_with_dataset(
    predictions: List[Dict],
    dataset_name: str = "princeton-nlp/SWE-bench_Verified",
    pipeline: EvaluationPipeline = None
) -> List[Dict]:
    """
    Evaluate predictions against a SWE-bench dataset.

    This integrates with your existing SWE-bench infrastructure.
    """
    # Load dataset
    print(f"Loading dataset: {dataset_name}")
    loader = DatasetLoader(source=dataset_name, hf_mode=True, split="test")

    # Build index
    dataset_index = {}
    for sample in loader.iter_samples():
        instance_id = sample.get('metadata', {}).get('instance_id')
        if instance_id:
            dataset_index[instance_id] = sample

    print(f"Loaded {len(dataset_index)} instances from dataset")

    # Evaluate each prediction
    results = []
    for i, pred in enumerate(predictions, 1):
        instance_id = pred.get('instance_id')
        model_patch = pred.get('model_patch')

        print(f"\n{'='*80}")
        print(f"Evaluating prediction {i}/{len(predictions)}: {instance_id}")
        print(f"{'='*80}")

        if not instance_id or instance_id not in dataset_index:
            print(f"  ✗ Instance not found in dataset: {instance_id}")
            results.append({
                'instance_id': instance_id,
                'status': 'error',
                'error': 'Instance not found in dataset'
            })
            continue

        sample = dataset_index[instance_id]

        # Prepare patch data for evaluation
        patch_data = {
            'id': instance_id,
            'diff': model_patch,
            'patched_code': model_patch,  # Will be extracted from repo
            'repo': sample.get('repo'),
            'base_commit': sample.get('base_commit')
        }

        # Evaluate
        result = pipeline.evaluate_patch(patch_data)
        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate patches with static analysis + dynamic fuzzing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate a single patch
  python scripts/eval_cli.py --patch patch.diff --code patched_code.py

  # Evaluate SWE-bench predictions
  python scripts/eval_cli.py --predictions preds.json --dataset SWE-bench_Verified

  # Batch evaluation
  python scripts/eval_cli.py --batch patches/ --output results.json

  # Skip static analysis
  python scripts/eval_cli.py --patch patch.diff --code code.py --no-static

  # Skip fuzzing
  python scripts/eval_cli.py --patch patch.diff --code code.py --no-fuzzing
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--patch',
        help='Path to patch file (unified diff)'
    )
    input_group.add_argument(
        '--predictions',
        help='Path to predictions JSON file (SWE-bench format)'
    )
    input_group.add_argument(
        '--batch',
        help='Path to directory containing multiple patches'
    )

    parser.add_argument(
        '--code',
        help='Path to patched code file (required with --patch)'
    )

    parser.add_argument(
        '--dataset',
        default='princeton-nlp/SWE-bench_Verified',
        help='SWE-bench dataset name (for --predictions mode)'
    )

    parser.add_argument(
        '--output',
        '-o',
        help='Output file for results (JSON)'
    )

    # Pipeline configuration
    parser.add_argument(
        '--image',
        default='/scratch0/ihbas/.containers/singularity/verifier-swebench.sif',
        help='Path to Singularity image'
    )

    parser.add_argument(
        '--no-static',
        action='store_true',
        help='Disable static verification'
    )

    parser.add_argument(
        '--no-fuzzing',
        action='store_true',
        help='Disable dynamic fuzzing'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='Fuzzing timeout in seconds (default: 120)'
    )

    parser.add_argument(
        '--static-threshold',
        type=float,
        default=0.5,
        help='Static quality threshold (0-1, default: 0.5)'
    )

    parser.add_argument(
        '--coverage-threshold',
        type=float,
        default=0.5,
        help='Coverage threshold (0-1, default: 0.5)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.patch and not args.code:
        parser.error("--code is required when using --patch")

    # Initialize pipeline
    print("Initializing evaluation pipeline...")
    pipeline = EvaluationPipeline(
        singularity_image_path=args.image,
        enable_static=not args.no_static,
        enable_fuzzing=not args.no_fuzzing,
        fuzzing_timeout=args.timeout,
        static_threshold=args.static_threshold,
        coverage_threshold=args.coverage_threshold
    )

    # Evaluate based on input mode
    results = []

    if args.patch:
        # Single patch mode
        patch_data = load_patch_from_files(args.patch, args.code)
        result = pipeline.evaluate_patch(patch_data)
        results = [result]

    elif args.predictions:
        # SWE-bench predictions mode
        predictions = load_predictions(args.predictions)
        results = evaluate_predictions_with_dataset(
            predictions,
            args.dataset,
            pipeline
        )

    elif args.batch:
        # Batch mode
        batch_dir = Path(args.batch)
        if not batch_dir.exists():
            print(f"Error: Batch directory not found: {batch_dir}")
            sys.exit(1)

        # Find all patch files
        patch_files = list(batch_dir.glob('*.diff')) + list(batch_dir.glob('*.patch'))
        print(f"Found {len(patch_files)} patch files")

        patches = []
        for patch_file in patch_files:
            # Look for corresponding code file
            code_file = patch_file.with_suffix('.py')
            if not code_file.exists():
                print(f"Warning: No code file found for {patch_file}, skipping")
                continue

            try:
                patch_data = load_patch_from_files(str(patch_file), str(code_file))
                patches.append(patch_data)
            except Exception as e:
                print(f"Warning: Failed to load {patch_file}: {e}")

        results = pipeline.evaluate_batch(patches, output_file=args.output)

    # Save results
    if args.output and not args.batch:  # batch mode already saves
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to: {args.output}")

    # Print summary
    if len(results) == 1:
        # Single result - print details
        result = results[0]
        print(f"\n{'='*80}")
        print(f"EVALUATION RESULT")
        print(f"{'='*80}")
        print(f"Patch ID: {result['patch_id']}")
        print(f"Verdict: {result['verdict']}")
        print(f"Reason: {result['reason']}")
        print(f"Execution Time: {result.get('execution_time', 0):.2f}s")

        if 'fuzzing_result' in result:
            fuzz = result['fuzzing_result']
            if 'coverage' in fuzz:
                cov = fuzz['coverage']
                print(f"\nFuzzing Coverage:")
                print(f"  Changed Lines: {cov.get('total_changed_lines', 0)}")
                print(f"  Covered Lines: {cov.get('total_covered_lines', 0)}")
                print(f"  Coverage: {cov.get('overall_coverage', 0):.1%}")

        print(f"{'='*80}\n")

    return 0 if all(r['verdict'] in ['ACCEPT', 'WARNING'] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
