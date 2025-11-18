"""
Cache Manager for Singularity .sif files.

Manages the cache of converted Singularity images, handles cleanup,
size limits, and organization by repository.
"""

import os
import shutil
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached .sif file."""

    instance_id: str
    path: Path
    size_bytes: int
    created_at: datetime
    last_accessed: datetime

    @property
    def size_mb(self) -> float:
        """Get size in MB."""
        return self.size_bytes / (1024 * 1024)

    @property
    def age_days(self) -> float:
        """Get age in days."""
        return (datetime.now() - self.created_at).total_seconds() / 86400

    def __repr__(self) -> str:
        return f"CacheEntry({self.instance_id}, {self.size_mb:.1f}MB, {self.age_days:.1f} days old)"


class CacheManager:
    """Manages Singularity image cache."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize cache manager.

        Args:
            config: Configuration instance
        """
        from .config import get_config

        self.config = config or get_config()
        self.cache_dir = self.config.singularity_cache_dir
        self.organize_by_repo = self.config.get("cache.organize_by_repo", True)

    def get_cache_path(self, instance_id: str, repo_name: Optional[str] = None) -> Path:
        """
        Get cache path for an instance.

        Args:
            instance_id: Instance ID
            repo_name: Optional repository name for organization

        Returns:
            Path to .sif file in cache
        """
        # Get naming pattern from config
        sif_naming = self.config.get("singularity.sif_naming", "{instance_id}.sif")
        filename = sif_naming.format(instance_id=instance_id, repo=repo_name or "unknown")

        if self.organize_by_repo and repo_name:
            # Organize by repository subdirectory
            repo_dir = self.cache_dir / repo_name
            repo_dir.mkdir(parents=True, exist_ok=True)
            return repo_dir / filename
        else:
            # Flat structure
            return self.cache_dir / filename

    def exists(self, instance_id: str, repo_name: Optional[str] = None) -> bool:
        """
        Check if instance is cached.

        Args:
            instance_id: Instance ID
            repo_name: Optional repository name

        Returns:
            True if cached .sif exists
        """
        cache_path = self.get_cache_path(instance_id, repo_name)
        exists = cache_path.exists() and cache_path.stat().st_size > 0

        if exists:
            logger.debug(f"Cache hit for {instance_id}: {cache_path}")
        else:
            logger.debug(f"Cache miss for {instance_id}")

        return exists

    def get(self, instance_id: str, repo_name: Optional[str] = None) -> Optional[Path]:
        """
        Get cached .sif file path.

        Args:
            instance_id: Instance ID
            repo_name: Optional repository name

        Returns:
            Path to .sif file if exists, None otherwise
        """
        if self.exists(instance_id, repo_name):
            cache_path = self.get_cache_path(instance_id, repo_name)
            # Update access time
            cache_path.touch(exist_ok=True)
            return cache_path
        return None

    def put(
        self, instance_id: str, source_path: Path, repo_name: Optional[str] = None
    ) -> Path:
        """
        Add a .sif file to cache.

        Args:
            instance_id: Instance ID
            source_path: Path to source .sif file
            repo_name: Optional repository name

        Returns:
            Path to cached .sif file
        """
        cache_path = self.get_cache_path(instance_id, repo_name)

        # Copy file to cache
        logger.info(f"Caching {instance_id} -> {cache_path}")
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        if source_path != cache_path:
            shutil.copy2(source_path, cache_path)
            logger.info(
                f"Cached {instance_id} ({cache_path.stat().st_size / (1024*1024):.1f} MB)"
            )

        return cache_path

    def remove(self, instance_id: str, repo_name: Optional[str] = None) -> bool:
        """
        Remove instance from cache.

        Args:
            instance_id: Instance ID
            repo_name: Optional repository name

        Returns:
            True if removed, False if not found
        """
        cache_path = self.get_cache_path(instance_id, repo_name)

        if cache_path.exists():
            size_mb = cache_path.stat().st_size / (1024 * 1024)
            cache_path.unlink()
            logger.info(f"Removed {instance_id} from cache ({size_mb:.1f} MB freed)")
            return True

        return False

    def list_cached(self) -> List[CacheEntry]:
        """
        List all cached .sif files.

        Returns:
            List of CacheEntry objects
        """
        entries = []

        for sif_file in self.cache_dir.rglob("*.sif"):
            try:
                stat = sif_file.stat()

                # Extract instance_id from filename
                instance_id = sif_file.stem

                entry = CacheEntry(
                    instance_id=instance_id,
                    path=sif_file,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    last_accessed=datetime.fromtimestamp(stat.st_atime),
                )
                entries.append(entry)

            except Exception as e:
                logger.warning(f"Error reading cache entry {sif_file}: {e}")

        return entries

    def get_cache_size(self) -> int:
        """
        Get total cache size in bytes.

        Returns:
            Total size in bytes
        """
        return sum(entry.size_bytes for entry in self.list_cached())

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        entries = self.list_cached()

        total_size_bytes = sum(e.size_bytes for e in entries)
        total_size_gb = total_size_bytes / (1024**3)

        stats = {
            "total_entries": len(entries),
            "total_size_bytes": total_size_bytes,
            "total_size_gb": round(total_size_gb, 2),
            "cache_dir": str(self.cache_dir),
            "oldest_entry": min(entries, key=lambda e: e.created_at) if entries else None,
            "newest_entry": max(entries, key=lambda e: e.created_at) if entries else None,
            "largest_entry": max(entries, key=lambda e: e.size_bytes) if entries else None,
        }

        return stats

    def cleanup_old(self, days: Optional[int] = None) -> int:
        """
        Remove cache entries older than specified days.

        Args:
            days: Age threshold in days (uses config default if None)

        Returns:
            Number of entries removed
        """
        if days is None:
            days = self.config.get("singularity.cleanup_after_days", 30)

        cutoff_date = datetime.now() - timedelta(days=days)
        entries = self.list_cached()

        removed = 0
        for entry in entries:
            if entry.created_at < cutoff_date:
                try:
                    entry.path.unlink()
                    logger.info(
                        f"Cleaned up old cache entry: {entry.instance_id} ({entry.age_days:.1f} days old)"
                    )
                    removed += 1
                except Exception as e:
                    logger.warning(f"Error removing {entry.path}: {e}")

        if removed > 0:
            logger.info(f"Cleaned up {removed} old cache entries (>{days} days)")

        return removed

    def cleanup_by_size(self, max_size_gb: Optional[float] = None) -> int:
        """
        Remove oldest entries until cache size is under limit.

        Args:
            max_size_gb: Maximum cache size in GB (uses config default if None)

        Returns:
            Number of entries removed
        """
        if max_size_gb is None:
            max_size_gb = self.config.get("singularity.max_cache_size_gb", 100)

        if max_size_gb <= 0:
            return 0  # Unlimited

        max_size_bytes = max_size_gb * (1024**3)
        entries = sorted(self.list_cached(), key=lambda e: e.last_accessed)

        current_size = sum(e.size_bytes for e in entries)
        removed = 0

        while current_size > max_size_bytes and entries:
            entry = entries.pop(0)
            try:
                entry.path.unlink()
                current_size -= entry.size_bytes
                logger.info(
                    f"Removed {entry.instance_id} to reduce cache size ({entry.size_mb:.1f} MB freed)"
                )
                removed += 1
            except Exception as e:
                logger.warning(f"Error removing {entry.path}: {e}")

        if removed > 0:
            logger.info(
                f"Cleaned up {removed} entries to meet size limit ({max_size_gb} GB)"
            )

        return removed

    def cleanup(
        self, max_age_days: Optional[int] = None, max_size_gb: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Perform comprehensive cleanup.

        Args:
            max_age_days: Maximum age in days
            max_size_gb: Maximum size in GB

        Returns:
            Dictionary with cleanup statistics
        """
        removed_old = self.cleanup_old(max_age_days)
        removed_size = self.cleanup_by_size(max_size_gb)

        return {
            "removed_by_age": removed_old,
            "removed_by_size": removed_size,
            "total_removed": removed_old + removed_size,
        }

    def clear(self) -> int:
        """
        Clear entire cache.

        Returns:
            Number of entries removed
        """
        entries = self.list_cached()
        removed = 0

        for entry in entries:
            try:
                entry.path.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"Error removing {entry.path}: {e}")

        logger.warning(f"Cleared entire cache: {removed} entries removed")
        return removed

    def verify_integrity(self) -> List[str]:
        """
        Verify integrity of cached .sif files.

        Returns:
            List of corrupted or invalid file paths
        """
        corrupted = []
        entries = self.list_cached()

        for entry in entries:
            # Check if file is readable and has reasonable size
            if entry.size_bytes < 1024:  # Less than 1KB is suspicious
                logger.warning(f"Suspicious file size for {entry.instance_id}: {entry.size_bytes} bytes")
                corrupted.append(str(entry.path))

        return corrupted

    def get_cache_report(self) -> str:
        """
        Generate a human-readable cache report.

        Returns:
            Formatted cache report string
        """
        stats = self.get_cache_stats()
        entries = self.list_cached()

        report = f"""
Singularity Cache Report
========================

Location: {stats['cache_dir']}
Total Entries: {stats['total_entries']}
Total Size: {stats['total_size_gb']} GB

"""

        if entries:
            # Group by repository
            by_repo: Dict[str, List[CacheEntry]] = {}
            for entry in entries:
                repo = entry.path.parent.name
                if repo not in by_repo:
                    by_repo[repo] = []
                by_repo[repo].append(entry)

            report += "By Repository:\n"
            for repo, repo_entries in sorted(by_repo.items()):
                repo_size_mb = sum(e.size_bytes for e in repo_entries) / (1024**2)
                report += f"  {repo}: {len(repo_entries)} entries, {repo_size_mb:.1f} MB\n"

            if stats["oldest_entry"]:
                report += f"\nOldest Entry: {stats['oldest_entry'].instance_id} ({stats['oldest_entry'].age_days:.1f} days)\n"
            if stats["largest_entry"]:
                report += f"Largest Entry: {stats['largest_entry'].instance_id} ({stats['largest_entry'].size_mb:.1f} MB)\n"

        return report
