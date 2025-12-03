#!/usr/bin/env python3
"""
Container cache cleanup utility.

Manages disk space by cleaning up old or unused Singularity containers.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys


def get_cache_info():
    """Get information about cached containers."""
    cache_dir = Path("/fs/nexus-scratch/ihbas/.cache/swebench_singularity")

    if not cache_dir.exists():
        return []

    containers = []

    for sif_file in cache_dir.rglob("*.sif"):
        stat = sif_file.stat()
        containers.append({
            'path': sif_file,
            'name': sif_file.stem,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'accessed': datetime.fromtimestamp(stat.st_atime),
        })

    # Sort by access time (oldest first)
    containers.sort(key=lambda x: x['accessed'])

    return containers


def get_disk_usage():
    """Get disk usage statistics."""
    result = subprocess.run(
        ['df', '/fs/nexus-scratch'],
        capture_output=True,
        text=True
    )

    lines = result.stdout.strip().split('\n')
    if len(lines) >= 2:
        parts = lines[1].split()
        total_gb = int(parts[1]) / (1024 * 1024)
        used_gb = int(parts[2]) / (1024 * 1024)
        available_gb = int(parts[3]) / (1024 * 1024)
        usage_pct = int(parts[4].rstrip('%'))

        return {
            'total_gb': total_gb,
            'used_gb': used_gb,
            'available_gb': available_gb,
            'usage_pct': usage_pct,
        }

    return None


def cleanup_by_age(containers, days=30, dry_run=False):
    """Remove containers older than N days."""
    cutoff = datetime.now() - timedelta(days=days)

    to_remove = [c for c in containers if c['accessed'] < cutoff]

    if not to_remove:
        print(f"No containers older than {days} days found.")
        return []

    print(f"Found {len(to_remove)} containers older than {days} days:")

    removed = []
    total_freed_mb = 0

    for container in to_remove:
        age_days = (datetime.now() - container['accessed']).days
        print(f"  - {container['name']}: {container['size_mb']:.1f} MB (last accessed {age_days} days ago)")

        if not dry_run:
            try:
                container['path'].unlink()
                removed.append(container['name'])
                total_freed_mb += container['size_mb']
                print(f"    ✓ Removed")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        else:
            total_freed_mb += container['size_mb']

    if dry_run:
        print(f"\n[DRY RUN] Would free {total_freed_mb:.1f} MB ({total_freed_mb/1024:.2f} GB)")
    else:
        print(f"\n✓ Freed {total_freed_mb:.1f} MB ({total_freed_mb/1024:.2f} GB)")

    return removed


def cleanup_keep_recent(containers, keep=10, dry_run=False):
    """Keep only the N most recently accessed containers."""
    if len(containers) <= keep:
        print(f"Only {len(containers)} containers exist (keeping all, limit is {keep})")
        return []

    # Sort by access time (newest first)
    containers_by_access = sorted(containers, key=lambda x: x['accessed'], reverse=True)

    to_remove = containers_by_access[keep:]

    print(f"Keeping {keep} most recent containers, removing {len(to_remove)}:")

    removed = []
    total_freed_mb = 0

    for container in to_remove:
        age_days = (datetime.now() - container['accessed']).days
        print(f"  - {container['name']}: {container['size_mb']:.1f} MB (last accessed {age_days} days ago)")

        if not dry_run:
            try:
                container['path'].unlink()
                removed.append(container['name'])
                total_freed_mb += container['size_mb']
                print(f"    ✓ Removed")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        else:
            total_freed_mb += container['size_mb']

    if dry_run:
        print(f"\n[DRY RUN] Would free {total_freed_mb:.1f} MB ({total_freed_mb/1024:.2f} GB)")
    else:
        print(f"\n✓ Freed {total_freed_mb:.1f} MB ({total_freed_mb/1024:.2f} GB)")

    return removed


def cleanup_by_space(containers, target_free_gb=10, dry_run=False):
    """Free up space until target is reached."""
    disk = get_disk_usage()

    if disk['available_gb'] >= target_free_gb:
        print(f"Already have {disk['available_gb']:.1f} GB free (target: {target_free_gb} GB)")
        return []

    needed_gb = target_free_gb - disk['available_gb']
    needed_mb = needed_gb * 1024

    print(f"Need to free {needed_gb:.2f} GB to reach target of {target_free_gb} GB free")
    print(f"Removing oldest containers until target is reached:")

    removed = []
    total_freed_mb = 0

    for container in containers:  # Already sorted by access time (oldest first)
        if total_freed_mb >= needed_mb:
            break

        age_days = (datetime.now() - container['accessed']).days
        print(f"  - {container['name']}: {container['size_mb']:.1f} MB (last accessed {age_days} days ago)")

        if not dry_run:
            try:
                container['path'].unlink()
                removed.append(container['name'])
                total_freed_mb += container['size_mb']
                print(f"    ✓ Removed")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        else:
            total_freed_mb += container['size_mb']

    if dry_run:
        print(f"\n[DRY RUN] Would free {total_freed_mb:.1f} MB ({total_freed_mb/1024:.2f} GB)")
    else:
        print(f"\n✓ Freed {total_freed_mb:.1f} MB ({total_freed_mb/1024:.2f} GB)")

    return removed


def show_status():
    """Show current cache status."""
    print("="*70)
    print("Container Cache Status")
    print("="*70)

    # Disk usage
    disk = get_disk_usage()
    if disk:
        print(f"\nDisk Usage:")
        print(f"  Total: {disk['total_gb']:.1f} GB")
        print(f"  Used: {disk['used_gb']:.1f} GB ({disk['usage_pct']}%)")
        print(f"  Available: {disk['available_gb']:.1f} GB")

        if disk['available_gb'] < 10:
            print(f"  ⚠️  WARNING: Low disk space!")
        elif disk['available_gb'] < 20:
            print(f"  ⚠️  Disk space getting low")

    # Cache info
    containers = get_cache_info()

    if not containers:
        print("\nNo containers cached.")
        return

    total_size_mb = sum(c['size_mb'] for c in containers)

    print(f"\nCached Containers: {len(containers)}")
    print(f"  Total size: {total_size_mb:.1f} MB ({total_size_mb/1024:.2f} GB)")
    print(f"  Average size: {total_size_mb/len(containers):.1f} MB")

    # Most recent
    most_recent = sorted(containers, key=lambda x: x['accessed'], reverse=True)[:5]
    print(f"\nMost Recently Accessed:")
    for c in most_recent:
        age_days = (datetime.now() - c['accessed']).days
        print(f"  - {c['name']}: {c['size_mb']:.1f} MB ({age_days} days ago)")

    # Oldest
    oldest = sorted(containers, key=lambda x: x['accessed'])[:5]
    print(f"\nOldest (by access time):")
    for c in oldest:
        age_days = (datetime.now() - c['accessed']).days
        print(f"  - {c['name']}: {c['size_mb']:.1f} MB ({age_days} days ago)")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Singularity container cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Show cache status (default action)'
    )

    parser.add_argument(
        '--cleanup-age',
        type=int,
        metavar='DAYS',
        help='Remove containers not accessed in N days'
    )

    parser.add_argument(
        '--keep-recent',
        type=int,
        metavar='N',
        help='Keep only N most recently accessed containers'
    )

    parser.add_argument(
        '--free-space',
        type=float,
        metavar='GB',
        help='Free up space until N GB is available'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without actually removing'
    )

    args = parser.parse_args()

    # Load cache info
    containers = get_cache_info()

    # Default action: show status
    if not any([args.cleanup_age, args.keep_recent, args.free_space]):
        show_status()
        return 0

    # Show initial status
    print("Initial Status:")
    print("-" * 70)
    disk = get_disk_usage()
    if disk:
        print(f"Available: {disk['available_gb']:.1f} GB")
    print(f"Containers: {len(containers)}")
    total_mb = sum(c['size_mb'] for c in containers)
    print(f"Total size: {total_mb:.1f} MB ({total_mb/1024:.2f} GB)")
    print()

    # Perform cleanup
    if args.cleanup_age:
        cleanup_by_age(containers, days=args.cleanup_age, dry_run=args.dry_run)

    elif args.keep_recent:
        cleanup_keep_recent(containers, keep=args.keep_recent, dry_run=args.dry_run)

    elif args.free_space:
        cleanup_by_space(containers, target_free_gb=args.free_space, dry_run=args.dry_run)

    # Show final status
    if not args.dry_run:
        print("\nFinal Status:")
        print("-" * 70)
        containers = get_cache_info()
        disk = get_disk_usage()
        if disk:
            print(f"Available: {disk['available_gb']:.1f} GB")
        print(f"Containers: {len(containers)}")
        total_mb = sum(c['size_mb'] for c in containers)
        print(f"Total size: {total_mb:.1f} MB ({total_mb/1024:.2f} GB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
