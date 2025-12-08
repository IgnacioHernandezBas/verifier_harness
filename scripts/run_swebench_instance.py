#!/usr/bin/env python3
"""
SWE-bench Singularity Instance Runner

Run SWE-bench evaluations for individual instances using Singularity containers.
Handles Docker image fetching, conversion, caching, and test execution.

Usage:
    # Run a single instance
    python scripts/run_swebench_instance.py --instance_id "django__django-12345"

    # Run with custom predictions/patch
    python scripts/run_swebench_instance.py \\
        --instance_id "pytest-dev__pytest-7490" \\
        --predictions_path "my_patch.diff"

    # Force rebuild container
    python scripts/run_swebench_instance.py \\
        --instance_id "flask__flask-4992" \\
        --force-rebuild

    # Custom cache directory
    python scripts/run_swebench_instance.py \\
        --instance_id "requests__requests-3362" \\
        --cache_dir "/custom/cache/path"

    # Just build container without running tests
    python scripts/run_swebench_instance.py \\
        --instance_id "sympy__sympy-20590" \\
        --build-only
"""

import sys
import argparse
import logging
import os
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DOCKER_CREDS = {
    "APPTAINER_DOCKER_USERNAME": "nacheitor12",
    "APPTAINER_DOCKER_PASSWORD": "wN/^4Me%,!5zz_q",
    "SINGULARITY_DOCKER_USERNAME": "nacheitor12",
    "SINGULARITY_DOCKER_PASSWORD": "wN/^4Me%,!5zz_q",
}

for key, value in DEFAULT_DOCKER_CREDS.items():
    os.environ.setdefault(key, value)

from swebench_singularity import (
    Config,
    SingularityBuilder,
    InstanceRunner,
    CacheManager,
)
from swebench_singularity.utils import (
    setup_logging,
    format_time,
    validate_instance_id,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SWE-bench instance evaluation with Singularity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Required arguments
    parser.add_argument(
        "--instance_id",
        required=True,
        help="SWE-bench instance ID (e.g., 'django__django-12345')",
    )

    # Optional arguments
    parser.add_argument(
        "--predictions_path",
        type=Path,
        help="Path to predictions/patch file",
    )

    parser.add_argument(
        "--cache_dir",
        type=Path,
        help="Cache directory for .sif files (overrides config)",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration YAML file",
    )

    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild container even if cached",
    )

    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build container, don't run tests",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (always rebuild)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        help="Test execution timeout in seconds",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (JSON)",
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
        help="Enable verbose output (DEBUG level)",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> bool:
    """
    Validate command-line arguments.

    Args:
        args: Parsed arguments

    Returns:
        True if valid, False otherwise
    """
    # Validate instance ID format
    if not validate_instance_id(args.instance_id):
        logger.error(
            f"Invalid instance ID format: {args.instance_id}\n"
            f"Expected format: <org>__<repo>-<version> (e.g., 'django__django-12345')"
        )
        return False

    # Validate predictions path if provided
    if args.predictions_path and not args.predictions_path.exists():
        logger.error(f"Predictions file not found: {args.predictions_path}")
        return False

    # Validate config file if provided
    if args.config and not args.config.exists():
        logger.error(f"Config file not found: {args.config}")
        return False

    return True


def build_container(
    builder: SingularityBuilder, instance_id: str, force_rebuild: bool
) -> Optional[Path]:
    """
    Build Singularity container for instance.

    Args:
        builder: SingularityBuilder instance
        instance_id: Instance ID
        force_rebuild: Force rebuild

    Returns:
        Path to .sif file if successful, None otherwise
    """
    logger.info(f"Building container for {instance_id}...")

    # Check Singularity availability
    if not builder.check_singularity_available():
        logger.error("Singularity is not available. Please install Singularity.")
        return None

    # Build container
    result = builder.build_instance(instance_id, force_rebuild=force_rebuild)

    if result.success:
        logger.info(
            f"✓ Container ready: {result.sif_path} "
            f"({format_time(result.build_time_seconds)})"
        )
        return result.sif_path
    else:
        logger.error(f"✗ Container build failed: {result.error_message}")
        return None


def run_instance(
    runner: InstanceRunner,
    instance_id: str,
    predictions_path: Optional[Path],
    force_rebuild: bool,
    timeout: Optional[int],
) -> bool:
    """
    Run instance evaluation.

    Args:
        runner: InstanceRunner instance
        instance_id: Instance ID
        predictions_path: Path to predictions file
        force_rebuild: Force rebuild
        timeout: Execution timeout

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"\n{'=' * 70}")
    logger.info(f"Running SWE-bench Instance: {instance_id}")
    logger.info(f"{'=' * 70}\n")

    # Run evaluation
    result = runner.run_swebench_instance(
        instance_id=instance_id,
        predictions_path=predictions_path,
        force_rebuild=force_rebuild,
    )

    # Display results
    logger.info(f"\n{'=' * 70}")
    logger.info("Results")
    logger.info(f"{'=' * 70}")
    logger.info(f"Instance ID: {result.instance_id}")
    logger.info(f"Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    logger.info(f"Tests Passed: {result.passed_tests}/{result.total_tests}")
    logger.info(f"Execution Time: {format_time(result.execution_time_seconds)}")

    if result.error_message:
        logger.error(f"Error: {result.error_message}")

    logger.info(f"{'=' * 70}\n")

    return result.success


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_logging(level=log_level, log_file=str(args.log_file) if args.log_file else None)

    logger.info("SWE-bench Singularity Instance Runner")
    logger.info(f"Instance ID: {args.instance_id}")

    # Validate arguments
    if not validate_args(args):
        return 1

    # Load configuration
    config = Config(config_path=str(args.config) if args.config else None)

    # Override cache directory if specified
    if args.cache_dir:
        config.set("singularity.cache_dir", str(args.cache_dir))

    # Disable caching if requested
    if args.no_cache:
        config.set("cache.enabled", False)

    # Set timeout if specified
    if args.timeout:
        config.set("execution.test_timeout", args.timeout)

    # Initialize components
    builder = SingularityBuilder(config)
    runner = InstanceRunner(config)

    # Build-only mode
    if args.build_only:
        sif_path = build_container(builder, args.instance_id, args.force_rebuild)
        if sif_path:
            logger.info(f"Container built successfully: {sif_path}")
            return 0
        else:
            logger.error("Container build failed")
            return 1

    # Run full evaluation
    success = run_instance(
        runner=runner,
        instance_id=args.instance_id,
        predictions_path=args.predictions_path,
        force_rebuild=args.force_rebuild,
        timeout=args.timeout,
    )

    # Save results if output file specified
    if args.output:
        # TODO: Save results to JSON file
        logger.info(f"Results saved to: {args.output}")

    # Display cache statistics
    cache = CacheManager(config)
    stats = cache.get_cache_stats()
    logger.info(f"\nCache: {stats['total_entries']} entries, {stats['total_size_gb']} GB")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
