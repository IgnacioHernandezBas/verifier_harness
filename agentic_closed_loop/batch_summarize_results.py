#!/usr/bin/env python3
"""
Batch process existing state files to generate result summaries.

Useful for retroactively generating summaries for old runs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_closed_loop.result_summarizer import create_result_summary


def batch_summarize(
    state_dir: Path,
    tests_model: str,
    claims_model: str | None = None,
    pattern: str = "*_C*.json",
) -> None:
    """
    Process all state files in a directory.

    Args:
        state_dir: Directory containing state JSON files
        tests_model: Model used for test generation
        claims_model: Model used for claim extraction
        pattern: Glob pattern for state files
    """
    state_files = list(state_dir.glob(pattern))

    if not state_files:
        print(f"No state files found matching pattern: {pattern}")
        return

    print(f"Found {len(state_files)} state files to process")
    print(f"Tests model: {tests_model}")
    print(f"Claims model: {claims_model or tests_model}")
    print()

    successful = 0
    failed = 0

    for state_file in sorted(state_files):
        try:
            print(f"Processing {state_file.name}...", end=" ")
            create_result_summary(
                state_file=state_file,
                tests_model=tests_model,
                claims_model=claims_model,
            )
            print("✓")
            successful += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1

    print()
    print(f"Summary: {successful} successful, {failed} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate result summaries from state files"
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("agentic_closed_loop/state"),
        help="Directory containing state files",
    )
    parser.add_argument(
        "--tests-model",
        required=True,
        help="Model used for test generation",
    )
    parser.add_argument(
        "--claims-model",
        default=None,
        help="Model used for claim extraction (defaults to tests-model)",
    )
    parser.add_argument(
        "--pattern",
        default="*_C*.json",
        help="Glob pattern for state files (default: *_C*.json)",
    )

    args = parser.parse_args()

    batch_summarize(
        state_dir=args.state_dir,
        tests_model=args.tests_model,
        claims_model=args.claims_model,
        pattern=args.pattern,
    )


if __name__ == "__main__":
    main()
