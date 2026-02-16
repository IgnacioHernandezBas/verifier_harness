#!/usr/bin/env python3
"""
Migrate existing outputs from flat structure to model-specific structure.

This script helps users transition their existing claim extraction outputs,
test generation outputs, and agentic loop state/logs to the new model-specific
directory structure.

Usage:
  python migrate_to_model_structure.py --model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
  python migrate_to_model_structure.py --model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" --dry-run
  python migrate_to_model_structure.py --model "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" --claims-only
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from common.model_paths import ModelPaths


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Migrate existing outputs to model-specific directory structure."
    )
    ap.add_argument(
        "--model",
        required=True,
        help="Model name to use for the migration (e.g., 'Qwen/Qwen2.5-Coder-32B-Instruct-AWQ')",
    )
    ap.add_argument(
        "--base_dir",
        type=Path,
        default=Path.cwd(),
        help="Base directory (defaults to current working directory)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually moving files",
    )
    ap.add_argument(
        "--claims-only",
        action="store_true",
        help="Only migrate claim extraction outputs",
    )
    ap.add_argument(
        "--tests-only",
        action="store_true",
        help="Only migrate test generation outputs",
    )
    ap.add_argument(
        "--agentic-only",
        action="store_true",
        help="Only migrate agentic loop state and logs",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in destination",
    )
    return ap.parse_args()


def migrate_claims(
    base_dir: Path,
    model_paths: ModelPaths,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Migrate claim extraction outputs."""
    old_claims_dir = base_dir / "claim_extraction" / "claims_out"
    new_claims_dir = model_paths.claims_dir()

    if not old_claims_dir.exists():
        return {"status": "skipped", "reason": "old claims directory does not exist"}

    # Find all JSON files in old directory (excluding model-specific subdirs)
    claim_files = [
        f
        for f in old_claims_dir.rglob("*.json")
        if f.is_file() and not any(
            # Skip if already in a model-specific subdirectory
            part for part in f.relative_to(old_claims_dir).parts[:-1]
            if not part.startswith(".")
        )
    ]

    results: Dict[str, Any] = {
        "status": "success",
        "total_files": len(claim_files),
        "migrated": 0,
        "skipped": 0,
        "errors": [],
    }

    if dry_run:
        print(f"[DRY RUN] Would migrate {len(claim_files)} claim files:")
        print(f"  From: {old_claims_dir}")
        print(f"  To:   {new_claims_dir}")

    for claim_file in claim_files:
        dest_file = new_claims_dir / claim_file.name

        if dest_file.exists() and not force:
            results["skipped"] += 1
            if dry_run:
                print(f"  SKIP (exists): {claim_file.name}")
            continue

        if dry_run:
            print(f"  MIGRATE: {claim_file.name}")
            results["migrated"] += 1
        else:
            try:
                new_claims_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(claim_file, dest_file)
                results["migrated"] += 1
                print(f"  ✓ Migrated: {claim_file.name}")
            except Exception as e:
                results["errors"].append({"file": str(claim_file), "error": str(e)})
                print(f"  ✗ Error migrating {claim_file.name}: {e}")

    return results


def migrate_tests(
    base_dir: Path,
    model_paths: ModelPaths,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Migrate test generation outputs."""
    old_tests_dir = base_dir / "claim_test_generation" / "tests_out"
    new_tests_root = model_paths.tests_root()

    if not old_tests_dir.exists():
        return {"status": "skipped", "reason": "old tests directory does not exist"}

    # Find all instance directories (skip model-specific subdirs)
    instance_dirs = [
        d
        for d in old_tests_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]

    # Filter out directories that look like model slugs
    # (heuristic: if they contain subdirectories that look like instance IDs)
    actual_instance_dirs = []
    for d in instance_dirs:
        subdirs = [sd for sd in d.iterdir() if sd.is_dir()]
        if subdirs:
            # This is likely a model slug directory, skip it
            continue
        actual_instance_dirs.append(d)

    results: Dict[str, Any] = {
        "status": "success",
        "total_instances": len(actual_instance_dirs),
        "migrated": 0,
        "skipped": 0,
        "errors": [],
    }

    if dry_run:
        print(f"[DRY RUN] Would migrate {len(actual_instance_dirs)} test directories:")
        print(f"  From: {old_tests_dir}")
        print(f"  To:   {new_tests_root}")

    for instance_dir in actual_instance_dirs:
        dest_dir = new_tests_root / instance_dir.name

        if dest_dir.exists() and not force:
            results["skipped"] += 1
            if dry_run:
                print(f"  SKIP (exists): {instance_dir.name}/")
            continue

        if dry_run:
            print(f"  MIGRATE: {instance_dir.name}/")
            results["migrated"] += 1
        else:
            try:
                new_tests_root.mkdir(parents=True, exist_ok=True)
                if dest_dir.exists() and force:
                    shutil.rmtree(dest_dir)
                shutil.copytree(instance_dir, dest_dir)
                results["migrated"] += 1
                print(f"  ✓ Migrated: {instance_dir.name}/")
            except Exception as e:
                results["errors"].append({"dir": str(instance_dir), "error": str(e)})
                print(f"  ✗ Error migrating {instance_dir.name}/: {e}")

    return results


def migrate_agentic(
    base_dir: Path,
    model_paths: ModelPaths,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Migrate agentic loop state and logs."""
    old_state_dir = base_dir / "agentic_closed_loop" / "state"
    old_logs_dir = base_dir / "agentic_closed_loop" / "logs"
    new_state_dir = model_paths.state_dir()
    new_logs_dir = model_paths.logs_dir()

    results: Dict[str, Any] = {
        "status": "success",
        "state_files": {"total": 0, "migrated": 0, "skipped": 0, "errors": []},
        "log_files": {"total": 0, "migrated": 0, "skipped": 0, "errors": []},
    }

    # Migrate state files
    if old_state_dir.exists():
        state_files = [
            f
            for f in old_state_dir.rglob("*.json")
            if f.is_file() and not any(
                part for part in f.relative_to(old_state_dir).parts[:-1]
            )
        ]

        results["state_files"]["total"] = len(state_files)

        if dry_run:
            print(f"[DRY RUN] Would migrate {len(state_files)} state files:")
            print(f"  From: {old_state_dir}")
            print(f"  To:   {new_state_dir}")

        for state_file in state_files:
            dest_file = new_state_dir / state_file.name

            if dest_file.exists() and not force:
                results["state_files"]["skipped"] += 1
                if dry_run:
                    print(f"  SKIP (exists): {state_file.name}")
                continue

            if dry_run:
                print(f"  MIGRATE: {state_file.name}")
                results["state_files"]["migrated"] += 1
            else:
                try:
                    new_state_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(state_file, dest_file)
                    results["state_files"]["migrated"] += 1
                    print(f"  ✓ Migrated state: {state_file.name}")
                except Exception as e:
                    results["state_files"]["errors"].append(
                        {"file": str(state_file), "error": str(e)}
                    )
                    print(f"  ✗ Error migrating {state_file.name}: {e}")

    # Migrate log files
    if old_logs_dir.exists():
        log_files = [
            f
            for f in old_logs_dir.rglob("*.jsonl")
            if f.is_file() and not any(
                part for part in f.relative_to(old_logs_dir).parts[:-1]
            )
        ]

        results["log_files"]["total"] = len(log_files)

        if dry_run:
            print(f"[DRY RUN] Would migrate {len(log_files)} log files:")
            print(f"  From: {old_logs_dir}")
            print(f"  To:   {new_logs_dir}")

        for log_file in log_files:
            dest_file = new_logs_dir / log_file.name

            if dest_file.exists() and not force:
                results["log_files"]["skipped"] += 1
                if dry_run:
                    print(f"  SKIP (exists): {log_file.name}")
                continue

            if dry_run:
                print(f"  MIGRATE: {log_file.name}")
                results["log_files"]["migrated"] += 1
            else:
                try:
                    new_logs_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(log_file, dest_file)
                    results["log_files"]["migrated"] += 1
                    print(f"  ✓ Migrated log: {log_file.name}")
                except Exception as e:
                    results["log_files"]["errors"].append(
                        {"file": str(log_file), "error": str(e)}
                    )
                    print(f"  ✗ Error migrating {log_file.name}: {e}")

    return results


def main() -> None:
    args = parse_args()

    model_paths = ModelPaths(
        model_name=args.model,
        base_dir=args.base_dir,
        use_model_subdirs=True,
    )

    print(f"Migration Configuration:")
    print(f"  Model: {args.model}")
    print(f"  Model slug: {model_paths.model_slug}")
    print(f"  Base directory: {args.base_dir}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Force overwrite: {args.force}")
    print()

    all_results: Dict[str, Any] = {}

    # Determine what to migrate
    migrate_all = not (args.claims_only or args.tests_only or args.agentic_only)

    if migrate_all or args.claims_only:
        print("=" * 60)
        print("MIGRATING CLAIMS")
        print("=" * 60)
        all_results["claims"] = migrate_claims(
            args.base_dir, model_paths, args.dry_run, args.force
        )
        print()

    if migrate_all or args.tests_only:
        print("=" * 60)
        print("MIGRATING TESTS")
        print("=" * 60)
        all_results["tests"] = migrate_tests(
            args.base_dir, model_paths, args.dry_run, args.force
        )
        print()

    if migrate_all or args.agentic_only:
        print("=" * 60)
        print("MIGRATING AGENTIC LOOP STATE & LOGS")
        print("=" * 60)
        all_results["agentic"] = migrate_agentic(
            args.base_dir, model_paths, args.dry_run, args.force
        )
        print()

    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(json.dumps(all_results, indent=2))

    if args.dry_run:
        print()
        print("This was a dry run. No files were actually moved.")
        print(f"To perform the migration, run without --dry-run:")
        print(f"  python migrate_to_model_structure.py --model \"{args.model}\"")


if __name__ == "__main__":
    main()
