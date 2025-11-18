#!/usr/bin/env python3
"""
SWE-bench Singularity Batch Runner

Run SWE-bench evaluations for multiple instances in parallel using Singularity containers.
Supports parallel execution, batch processing, and progress tracking.

Usage:
    # Run multiple instances from list
    python run_swebench_batch.py --instance_list instances.txt

    # Run with predictions file
    python run_swebench_batch.py \\
        --predictions predictions.json \\
        --output results.json

    # Parallel execution with 10 workers
    python run_swebench_batch.py \\
        --instance_list instances.txt \\
        --workers 10

    # Filter by repository
    python run_swebench_batch.py \\
        --instance_list instances.txt \\
        --repo pytest

    # Resume from previous run
    python run_swebench_batch.py \\
        --instance_list instances.txt \\
        --resume results_partial.json
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from swebench_singularity import (
    Config,
    SingularityBuilder,
    InstanceRunner,
    CacheManager,
)
from swebench_singularity.utils import (
    setup_logging,
    format_time,
    parse_instance_list,
    ProgressBar,
    save_json,
    load_json,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SWE-bench batch evaluation with Singularity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--instance_list",
        type=Path,
        help="Path to file with instance IDs (one per line or JSON)",
    )
    input_group.add_argument(
        "--predictions",
        type=Path,
        help="Path to predictions JSON file",
    )

    # Output
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Output file for results (JSON)",
    )

    # Execution options
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel workers (default: from config)",
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run sequentially instead of in parallel",
    )

    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild all containers",
    )

    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build containers, don't run tests",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure",
    )

    # Filtering
    parser.add_argument(
        "--repo",
        help="Filter instances by repository name (e.g., 'pytest', 'django')",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of instances to process",
    )

    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip first N instances",
    )

    # Resume from previous run
    parser.add_argument(
        "--resume",
        type=Path,
        help="Resume from previous results file (skip completed instances)",
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration YAML file",
    )

    parser.add_argument(
        "--cache_dir",
        type=Path,
        help="Cache directory for .sif files",
    )

    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def load_instances(args: argparse.Namespace) -> List[str]:
    """
    Load instance IDs from input source.

    Args:
        args: Command-line arguments

    Returns:
        List of instance IDs
    """
    if args.instance_list:
        logger.info(f"Loading instances from: {args.instance_list}")
        instances = parse_instance_list(args.instance_list)

    elif args.predictions:
        logger.info(f"Loading instances from predictions: {args.predictions}")
        data = load_json(args.predictions)

        if isinstance(data, dict):
            instances = list(data.keys())
        elif isinstance(data, list):
            instances = [item.get("instance_id") for item in data if "instance_id" in item]
        else:
            raise ValueError(f"Invalid predictions format: {args.predictions}")

    else:
        raise ValueError("No input source specified")

    logger.info(f"Loaded {len(instances)} instances")
    return instances


def filter_instances(
    instances: List[str],
    repo_filter: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    completed: Optional[set] = None,
) -> List[str]:
    """
    Filter instance list based on criteria.

    Args:
        instances: List of instance IDs
        repo_filter: Repository name to filter by
        skip: Number of instances to skip
        limit: Maximum number of instances
        completed: Set of already completed instance IDs

    Returns:
        Filtered list of instance IDs
    """
    # Filter by repository
    if repo_filter:
        original_count = len(instances)
        instances = [
            i for i in instances
            if repo_filter.lower() in i.lower()
        ]
        logger.info(
            f"Filtered by repo '{repo_filter}': {len(instances)}/{original_count} instances"
        )

    # Filter out completed instances
    if completed:
        original_count = len(instances)
        instances = [i for i in instances if i not in completed]
        logger.info(
            f"Skipping {original_count - len(instances)} completed instances"
        )

    # Skip instances
    if skip > 0:
        instances = instances[skip:]
        logger.info(f"Skipped first {skip} instances")

    # Limit instances
    if limit:
        instances = instances[:limit]
        logger.info(f"Limited to {limit} instances")

    return instances


def run_single_instance(
    instance_id: str,
    config_path: Optional[str],
    force_rebuild: bool,
    build_only: bool,
) -> Dict[str, Any]:
    """
    Run a single instance (for parallel execution).

    Args:
        instance_id: Instance ID
        config_path: Path to config file
        force_rebuild: Force rebuild
        build_only: Only build container

    Returns:
        Result dictionary
    """
    try:
        # Initialize components (fresh for each worker)
        config = Config(config_path)
        runner = InstanceRunner(config)

        if build_only:
            builder = SingularityBuilder(config)
            result = builder.build_instance(instance_id, force_rebuild)

            return {
                "instance_id": instance_id,
                "success": result.success,
                "error": result.error_message,
                "build_time": result.build_time_seconds,
                "from_cache": result.from_cache,
            }
        else:
            result = runner.run_swebench_instance(
                instance_id=instance_id,
                force_rebuild=force_rebuild,
            )

            return result.to_dict()

    except Exception as e:
        logger.error(f"Error processing {instance_id}: {e}")
        return {
            "instance_id": instance_id,
            "success": False,
            "error": str(e),
        }


def run_batch_parallel(
    instances: List[str],
    config_path: Optional[str],
    workers: int,
    force_rebuild: bool,
    build_only: bool,
    fail_fast: bool,
    output_path: Path,
) -> Dict[str, Any]:
    """
    Run batch processing in parallel.

    Args:
        instances: List of instance IDs
        config_path: Path to config file
        workers: Number of parallel workers
        force_rebuild: Force rebuild
        build_only: Only build containers
        fail_fast: Stop on first failure
        output_path: Output file path

    Returns:
        Results dictionary
    """
    results = {}
    failed = False

    logger.info(f"Running {len(instances)} instances with {workers} workers...")

    # Progress tracking
    progress = ProgressBar(total=len(instances), prefix="Progress")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_instance = {
            executor.submit(
                run_single_instance,
                instance_id,
                config_path,
                force_rebuild,
                build_only,
            ): instance_id
            for instance_id in instances
        }

        # Process completed tasks
        for future in as_completed(future_to_instance):
            instance_id = future_to_instance[future]

            try:
                result = future.result()
                results[instance_id] = result

                # Update progress
                progress.update()

                # Log result
                if result["success"]:
                    logger.debug(f"✓ {instance_id}")
                else:
                    logger.warning(f"✗ {instance_id}: {result.get('error', 'Unknown error')}")
                    failed = True

                # Save intermediate results
                save_json(results, output_path)

                # Fail fast
                if fail_fast and failed:
                    logger.error("Stopping due to failure (fail-fast mode)")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

            except Exception as e:
                logger.error(f"Error processing {instance_id}: {e}")
                results[instance_id] = {
                    "instance_id": instance_id,
                    "success": False,
                    "error": str(e),
                }
                progress.update()

    return results


def run_batch_sequential(
    instances: List[str],
    config: Config,
    force_rebuild: bool,
    build_only: bool,
    fail_fast: bool,
    output_path: Path,
) -> Dict[str, Any]:
    """
    Run batch processing sequentially.

    Args:
        instances: List of instance IDs
        config: Configuration
        force_rebuild: Force rebuild
        build_only: Only build containers
        fail_fast: Stop on first failure
        output_path: Output file path

    Returns:
        Results dictionary
    """
    results = {}

    # Initialize components
    if build_only:
        builder = SingularityBuilder(config)
    else:
        runner = InstanceRunner(config)

    # Progress tracking
    progress = ProgressBar(total=len(instances), prefix="Progress")

    for i, instance_id in enumerate(instances, 1):
        logger.info(f"\n[{i}/{len(instances)}] Processing: {instance_id}")

        try:
            if build_only:
                result = builder.build_instance(instance_id, force_rebuild)
                results[instance_id] = {
                    "instance_id": instance_id,
                    "success": result.success,
                    "error": result.error_message,
                    "build_time": result.build_time_seconds,
                    "from_cache": result.from_cache,
                }
            else:
                result = runner.run_swebench_instance(
                    instance_id=instance_id,
                    force_rebuild=force_rebuild,
                )
                results[instance_id] = result.to_dict()

            # Update progress
            progress.update()

            # Log result
            if results[instance_id]["success"]:
                logger.info(f"✓ {instance_id}")
            else:
                error = results[instance_id].get("error", "Unknown error")
                logger.error(f"✗ {instance_id}: {error}")

                if fail_fast:
                    logger.error("Stopping due to failure (fail-fast mode)")
                    break

            # Save intermediate results
            save_json(results, output_path)

        except Exception as e:
            logger.error(f"Error processing {instance_id}: {e}")
            results[instance_id] = {
                "instance_id": instance_id,
                "success": False,
                "error": str(e),
            }
            progress.update()

            if fail_fast:
                break

    return results


def generate_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate summary statistics from results.

    Args:
        results: Results dictionary

    Returns:
        Summary dictionary
    """
    total = len(results)
    successful = sum(1 for r in results.values() if r.get("success", False))
    failed = total - successful

    # Calculate additional metrics
    from_cache = sum(1 for r in results.values() if r.get("from_cache", False))
    total_time = sum(
        r.get("execution_time_seconds", r.get("build_time", 0))
        for r in results.values()
    )

    summary = {
        "total_instances": total,
        "successful": successful,
        "failed": failed,
        "success_rate": successful / total if total > 0 else 0,
        "from_cache": from_cache,
        "total_time_seconds": total_time,
        "average_time_seconds": total_time / total if total > 0 else 0,
    }

    return summary


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_logging(level=log_level, log_file=str(args.log_file) if args.log_file else None)

    logger.info("SWE-bench Singularity Batch Runner")
    logger.info(f"Output: {args.output}")

    # Load configuration
    config = Config(config_path=str(args.config) if args.config else None)

    # Override settings from args
    if args.cache_dir:
        config.set("singularity.cache_dir", str(args.cache_dir))

    if args.workers:
        config.set("parallel.max_workers", args.workers)

    if args.fail_fast:
        config.set("parallel.fail_fast", True)

    # Load instances
    instances = load_instances(args)

    # Load completed instances from resume file
    completed = set()
    if args.resume and args.resume.exists():
        logger.info(f"Resuming from: {args.resume}")
        resume_data = load_json(args.resume)
        completed = set(resume_data.keys())
        logger.info(f"Found {len(completed)} completed instances")

    # Filter instances
    instances = filter_instances(
        instances=instances,
        repo_filter=args.repo,
        skip=args.skip,
        limit=args.limit,
        completed=completed,
    )

    if not instances:
        logger.warning("No instances to process after filtering")
        return 0

    logger.info(f"Processing {len(instances)} instances")

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Run batch processing
    start_time = datetime.now()

    if args.sequential:
        logger.info("Running in sequential mode")
        results = run_batch_sequential(
            instances=instances,
            config=config,
            force_rebuild=args.force_rebuild,
            build_only=args.build_only,
            fail_fast=args.fail_fast,
            output_path=args.output,
        )
    else:
        workers = args.workers or config.get("parallel.max_workers", 10)
        logger.info(f"Running in parallel mode with {workers} workers")
        results = run_batch_parallel(
            instances=instances,
            config_path=str(args.config) if args.config else None,
            workers=workers,
            force_rebuild=args.force_rebuild,
            build_only=args.build_only,
            fail_fast=args.fail_fast,
            output_path=args.output,
        )

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # Generate summary
    summary = generate_summary(results)
    summary["start_time"] = start_time.isoformat()
    summary["end_time"] = end_time.isoformat()
    summary["elapsed_seconds"] = elapsed

    # Save final results with summary
    final_output = {
        "summary": summary,
        "results": results,
    }
    save_json(final_output, args.output)

    # Display summary
    logger.info(f"\n{'=' * 70}")
    logger.info("Batch Processing Summary")
    logger.info(f"{'=' * 70}")
    logger.info(f"Total Instances: {summary['total_instances']}")
    logger.info(f"Successful: {summary['successful']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Success Rate: {summary['success_rate']:.1%}")
    logger.info(f"From Cache: {summary['from_cache']}")
    logger.info(f"Total Time: {format_time(elapsed)}")
    logger.info(f"Average Time: {format_time(summary['average_time_seconds'])}")
    logger.info(f"Results saved to: {args.output}")
    logger.info(f"{'=' * 70}\n")

    # Display cache statistics
    cache = CacheManager(config)
    stats = cache.get_cache_stats()
    logger.info(f"Cache: {stats['total_entries']} entries, {stats['total_size_gb']} GB")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
