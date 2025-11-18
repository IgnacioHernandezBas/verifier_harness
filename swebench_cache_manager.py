#!/usr/bin/env python3
"""
SWE-bench Singularity Cache Manager

Utility for managing the Singularity .sif file cache.
Supports viewing, cleaning, and maintaining the cache.

Usage:
    # View cache statistics
    python swebench_cache_manager.py stats

    # List all cached instances
    python swebench_cache_manager.py list

    # Clean old entries (>30 days)
    python swebench_cache_manager.py clean --days 30

    # Clean by size limit
    python swebench_cache_manager.py clean --max-size 50

    # Remove specific instance
    python swebench_cache_manager.py remove --instance_id "django__django-12345"

    # Clear entire cache
    python swebench_cache_manager.py clear

    # Verify cache integrity
    python swebench_cache_manager.py verify

    # Generate detailed report
    python swebench_cache_manager.py report
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from swebench_singularity import Config, CacheManager
from swebench_singularity.utils import (
    setup_logging,
    format_bytes,
    confirm_action,
    print_table,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Manage SWE-bench Singularity cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # stats: Show cache statistics
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")

    # list: List cached instances
    list_parser = subparsers.add_parser("list", help="List cached instances")
    list_parser.add_argument(
        "--repo",
        help="Filter by repository name",
    )
    list_parser.add_argument(
        "--sort",
        choices=["size", "age", "name"],
        default="name",
        help="Sort by criteria",
    )

    # clean: Clean cache
    clean_parser = subparsers.add_parser("clean", help="Clean cache")
    clean_parser.add_argument(
        "--days",
        type=int,
        help="Remove entries older than N days",
    )
    clean_parser.add_argument(
        "--max-size",
        type=float,
        help="Remove oldest entries until cache is under N GB",
    )
    clean_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation",
    )

    # remove: Remove specific instance
    remove_parser = subparsers.add_parser("remove", help="Remove specific instance")
    remove_parser.add_argument(
        "--instance_id",
        required=True,
        help="Instance ID to remove",
    )
    remove_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation",
    )

    # clear: Clear entire cache
    clear_parser = subparsers.add_parser("clear", help="Clear entire cache")
    clear_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation",
    )

    # verify: Verify cache integrity
    verify_parser = subparsers.add_parser("verify", help="Verify cache integrity")

    # report: Generate detailed report
    report_parser = subparsers.add_parser("report", help="Generate detailed report")
    report_parser.add_argument(
        "--output",
        type=Path,
        help="Save report to file",
    )

    # Global options
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration YAML file",
    )

    parser.add_argument(
        "--cache_dir",
        type=Path,
        help="Cache directory (overrides config)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def cmd_stats(cache: CacheManager):
    """Display cache statistics."""
    stats = cache.get_cache_stats()

    print("\n" + "=" * 60)
    print("Singularity Cache Statistics")
    print("=" * 60)
    print(f"Location: {stats['cache_dir']}")
    print(f"Total Entries: {stats['total_entries']}")
    print(f"Total Size: {stats['total_size_gb']:.2f} GB")

    if stats['oldest_entry']:
        print(f"Oldest Entry: {stats['oldest_entry'].instance_id} ({stats['oldest_entry'].age_days:.1f} days)")

    if stats['newest_entry']:
        print(f"Newest Entry: {stats['newest_entry'].instance_id} ({stats['newest_entry'].age_days:.1f} days)")

    if stats['largest_entry']:
        print(f"Largest Entry: {stats['largest_entry'].instance_id} ({stats['largest_entry'].size_mb:.1f} MB)")

    print("=" * 60 + "\n")


def cmd_list(cache: CacheManager, repo_filter: Optional[str] = None, sort_by: str = "name"):
    """List cached instances."""
    entries = cache.list_cached()

    # Filter by repository
    if repo_filter:
        entries = [e for e in entries if repo_filter.lower() in e.instance_id.lower()]

    # Sort entries
    if sort_by == "size":
        entries = sorted(entries, key=lambda e: e.size_bytes, reverse=True)
    elif sort_by == "age":
        entries = sorted(entries, key=lambda e: e.created_at)
    else:  # name
        entries = sorted(entries, key=lambda e: e.instance_id)

    if not entries:
        print("No cached entries found")
        return

    # Prepare table data
    headers = ["Instance ID", "Size", "Age (days)", "Last Accessed"]
    rows = []

    for entry in entries:
        rows.append([
            entry.instance_id,
            format_bytes(entry.size_bytes),
            f"{entry.age_days:.1f}",
            entry.last_accessed.strftime("%Y-%m-%d %H:%M"),
        ])

    print_table(headers, rows, title=f"Cached Instances ({len(entries)} total)")


def cmd_clean(
    cache: CacheManager,
    days: Optional[int] = None,
    max_size: Optional[float] = None,
    skip_confirm: bool = False,
):
    """Clean cache."""
    if not days and not max_size:
        print("Error: Specify --days or --max-size")
        return 1

    # Show what will be cleaned
    if days:
        print(f"Cleaning entries older than {days} days...")
    if max_size:
        print(f"Cleaning to reduce cache size below {max_size} GB...")

    # Confirm
    if not skip_confirm:
        if not confirm_action("Proceed with cleanup?", default=False):
            print("Cleanup cancelled")
            return 0

    # Perform cleanup
    result = cache.cleanup(max_age_days=days, max_size_gb=max_size)

    print(f"\nCleanup complete:")
    print(f"  Removed by age: {result['removed_by_age']}")
    print(f"  Removed by size: {result['removed_by_size']}")
    print(f"  Total removed: {result['total_removed']}")

    # Show updated stats
    print()
    cmd_stats(cache)

    return 0


def cmd_remove(cache: CacheManager, instance_id: str, skip_confirm: bool = False):
    """Remove specific instance from cache."""
    # Check if instance exists
    if not cache.exists(instance_id):
        print(f"Instance not found in cache: {instance_id}")
        return 1

    # Confirm
    if not skip_confirm:
        if not confirm_action(f"Remove {instance_id} from cache?", default=False):
            print("Removal cancelled")
            return 0

    # Remove
    if cache.remove(instance_id):
        print(f"Removed {instance_id} from cache")
        return 0
    else:
        print(f"Failed to remove {instance_id}")
        return 1


def cmd_clear(cache: CacheManager, skip_confirm: bool = False):
    """Clear entire cache."""
    stats = cache.get_cache_stats()

    print(f"Warning: This will remove all {stats['total_entries']} cached entries ({stats['total_size_gb']:.2f} GB)")

    # Confirm
    if not skip_confirm:
        if not confirm_action("Are you sure you want to clear the entire cache?", default=False):
            print("Clear cancelled")
            return 0

    # Clear
    removed = cache.clear()
    print(f"Cleared cache: {removed} entries removed")

    return 0


def cmd_verify(cache: CacheManager):
    """Verify cache integrity."""
    print("Verifying cache integrity...")

    corrupted = cache.verify_integrity()

    if not corrupted:
        print("✓ Cache integrity verified - no issues found")
        return 0
    else:
        print(f"✗ Found {len(corrupted)} corrupted or suspicious files:")
        for path in corrupted:
            print(f"  - {path}")

        if confirm_action("Remove corrupted files?", default=False):
            for path in corrupted:
                try:
                    Path(path).unlink()
                    print(f"Removed: {path}")
                except Exception as e:
                    print(f"Error removing {path}: {e}")

        return 1


def cmd_report(cache: CacheManager, output_file: Optional[Path] = None):
    """Generate detailed cache report."""
    report = cache.get_cache_report()

    # Print to console
    print(report)

    # Save to file if specified
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {output_file}")

    return 0


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_logging(level=log_level)

    # Check if command was provided
    if not args.command:
        print("Error: No command specified")
        print("Use --help to see available commands")
        return 1

    # Load configuration
    config = Config(config_path=str(args.config) if args.config else None)

    # Override cache directory if specified
    if args.cache_dir:
        config.set("singularity.cache_dir", str(args.cache_dir))

    # Initialize cache manager
    cache = CacheManager(config)

    # Execute command
    try:
        if args.command == "stats":
            return cmd_stats(cache)

        elif args.command == "list":
            return cmd_list(cache, args.repo, args.sort)

        elif args.command == "clean":
            return cmd_clean(cache, args.days, args.max_size, args.yes)

        elif args.command == "remove":
            return cmd_remove(cache, args.instance_id, args.yes)

        elif args.command == "clear":
            return cmd_clear(cache, args.yes)

        elif args.command == "verify":
            return cmd_verify(cache)

        elif args.command == "report":
            return cmd_report(cache, args.output)

        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
