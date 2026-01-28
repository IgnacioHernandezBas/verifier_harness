#!/usr/bin/env python3
"""
Prepare SWE-bench Lite instances for the claim extractor.

This script loads a subset of issues, enriches them with the buggy code context
required by the prompt, and writes an `instances.json` file that can be consumed
by `claim_extraction.cli` (including the Slurm sbatch wrappers).
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from datasets import load_dataset  # type: ignore

from claim_extraction.pipeline.grounding import parse_unified_diff

logger = logging.getLogger("claim_extraction.prepare_instances")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare SWE-bench Lite instances (with code context) for the claim extractor."
    )
    parser.add_argument("--dataset", default="princeton-nlp/SWE-bench_Lite", help="HuggingFace dataset name")
    parser.add_argument("--split", default="test", help="Dataset split to use (default: test)")
    parser.add_argument("--output", required=True, help="Path to write instances.json")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of instances")
    parser.add_argument("--skip", type=int, default=0, help="Skip the first N matching instances")
    parser.add_argument("--repo", default=None, help="Filter by repo substring (e.g., 'scikit-learn/scikit-learn')")
    parser.add_argument(
        "--tier",
        default=None,
        help="Filter by tier (matches instance['tier'] or instance['metadata']['tier'] if available)",
    )
    parser.add_argument(
        "--instances-file",
        default=None,
        help="Optional text file with instance_ids (one per line) to include",
    )
    parser.add_argument(
        "--code-lines-before",
        type=int,
        default=30,
        help="Number of context lines before each diff hunk (default: 30)",
    )
    parser.add_argument(
        "--code-lines-after",
        type=int,
        default=30,
        help="Number of context lines after each diff hunk (default: 30)",
    )
    parser.add_argument(
        "--max-code-chars",
        type=int,
        default=22000,
        help="Maximum characters for the aggregated code context per instance",
    )
    parser.add_argument(
        "--repos-dir",
        default="repos_claim_extraction_cache",
        help="Directory used to cache cloned repositories",
    )
    parser.add_argument(
        "--keep-repos",
        action="store_true",
        help="Keep cloned repositories after the script finishes (default: remove clones created by this run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the instances that would be written (no cloning, no file output)",
    )
    return parser.parse_args()


def load_instance_filter(path: Optional[str]) -> Optional[Set[str]]:
    if not path:
        return None
    values: List[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                values.append(line)
    return set(values)


def normalize_instance(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    HuggingFace datasets return internal data structures; convert to plain dict with JSON-serializable fields.
    """
    out: Dict[str, Any] = {}
    for key, value in obj.items():
        if hasattr(value, "items"):
            out[key] = dict(value)  # type: ignore[arg-type]
        else:
            out[key] = value
    return out


def should_include_instance(
    instance: Dict[str, Any],
    *,
    repo_filter: Optional[str],
    tier_filter: Optional[str],
    allow_ids: Optional[Set[str]],
) -> bool:
    if allow_ids is not None and instance.get("instance_id") not in allow_ids:
        return False
    if repo_filter and repo_filter not in (instance.get("repo") or ""):
        return False
    if tier_filter:
        tier_val = instance.get("tier")
        if not tier_val:
            tier_val = (instance.get("metadata") or {}).get("tier") if isinstance(instance.get("metadata"), dict) else None
        if tier_val != tier_filter:
            return False
    return True


def ensure_repo_checkout(
    repo: str,
    base_commit: Optional[str],
    repos_dir: Path,
    cache: Dict[Tuple[str, str], Path],
    created_paths: List[Path],
) -> Path:
    commit_key = base_commit or "HEAD"
    cache_key = (repo, commit_key)
    if cache_key in cache:
        return cache[cache_key]

    repo_slug = repo.replace("/", "__")
    target_dir = repos_dir / repo_slug / commit_key
    if target_dir.exists():
        cache[cache_key] = target_dir
        return target_dir

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{repo}.git"
    logger.info("Cloning %s @ %s into %s", repo, commit_key, target_dir)
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(target_dir)],
        check=True,
        capture_output=True,
    )
    if base_commit:
        result = subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", base_commit],
            cwd=target_dir,
            capture_output=True,
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "fetch", "--unshallow"],
                cwd=target_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "fetch", "origin", base_commit],
                cwd=target_dir,
                check=True,
                capture_output=True,
            )
        subprocess.run(["git", "checkout", base_commit], cwd=target_dir, check=True, capture_output=True)

    cache[cache_key] = target_dir
    created_paths.append(target_dir)
    return target_dir


def merge_ranges(ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged: List[Tuple[int, int]] = [ranges[0]]
    for start, end in ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def collect_line_windows(
    patch: str,
    *,
    lines_before: int,
    lines_after: int,
) -> Dict[str, List[Tuple[int, int]]]:
    if not patch.strip():
        return {}

    parsed = parse_unified_diff(patch)
    per_file: Dict[str, List[Tuple[int, int]]] = {}
    for dl in parsed:
        if not dl.path:
            continue
        if dl.old_lineno is None:
            continue  # additions only exist in the new file (not part of buggy context)
        start = max(1, dl.old_lineno - lines_before)
        end = dl.old_lineno + lines_after
        per_file.setdefault(dl.path, []).append((start, end))

    return {path: merge_ranges(ranges) for path, ranges in per_file.items()}


def format_code_context(
    repo_path: Path,
    patch: str,
    *,
    commit_label: str,
    lines_before: int,
    lines_after: int,
    max_chars: int,
) -> str:
    file_windows = collect_line_windows(patch, lines_before=lines_before, lines_after=lines_after)
    if not file_windows:
        return ""

    parts: List[str] = []
    remaining = max_chars

    for rel_path, ranges in file_windows.items():
        abs_path = (repo_path / rel_path).resolve()
        try:
            file_text = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except FileNotFoundError:
            snippet = f"### File: {rel_path} (missing in checkout)\n[warning] File not found at {abs_path}"
            if remaining <= 0:
                break
            snippet = snippet[:remaining]
            parts.append(snippet)
            remaining -= len(snippet)
            continue

        header = f"### File: {rel_path} (base @ {commit_label})"
        snippet_lines: List[str] = []
        for start, end in ranges:
            snippet_lines.append(f"-- lines {start}-{end} --")
            for lineno in range(start, end + 1):
                if 1 <= lineno <= len(file_text):
                    snippet_lines.append(f"{lineno:>5}: {file_text[lineno - 1]}")
        file_block = header + "\n" + "\n".join(snippet_lines)
        if remaining <= 0:
            break
        if len(file_block) > remaining:
            file_block = file_block[:remaining]
        parts.append(file_block)
        remaining -= len(file_block)
        if remaining <= 0:
            break

    context = "\n\n".join(parts)
    if len(context) >= max_chars:
        context = context[:max_chars - 20] + "\n...\n[truncated]"
    return context


def load_touched_file_texts(
    repo_path: Optional[Path],
    patch: str,
    *,
    max_chars_per_file: int = 60000,
) -> Dict[str, str]:
    if repo_path is None or not patch:
        return {}

    parsed = parse_unified_diff(patch)
    rel_paths = {dl.path for dl in parsed if dl.path}
    files: Dict[str, str] = {}

    for rel_path in rel_paths:
        abs_path = (repo_path / rel_path).resolve()
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if max_chars_per_file and len(text) > max_chars_per_file:
            text = text[: max_chars_per_file - 20] + "\n...\n[truncated]"
        files[rel_path] = text

    return files


def build_instance_payload(
    instance: Dict[str, Any],
    *,
    repo_path: Optional[Path],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    payload = dict(instance)
    payload["code_context"] = ""
    payload["touched_files_text"] = {}

    patch = instance.get("patch") or ""
    commit_label = (instance.get("base_commit") or "HEAD")[:12]
    if repo_path is not None and patch:
        payload["code_context"] = format_code_context(
            repo_path,
            patch,
            commit_label=commit_label,
            lines_before=args.code_lines_before,
            lines_after=args.code_lines_after,
            max_chars=args.max_code_chars,
        )
        payload["touched_files_text"] = load_touched_file_texts(repo_path, patch)
    return payload


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    allowed_ids = load_instance_filter(args.instances_file)
    dataset = load_dataset(args.dataset, split=args.split)
    logger.info("Loaded dataset %s[%s] (%d rows)", args.dataset, args.split, len(dataset))

    repos_dir = Path(args.repos_dir).resolve()
    repo_cache: Dict[Tuple[str, str], Path] = {}
    created_paths: List[Path] = []

    selected: List[Dict[str, Any]] = []
    skipped = args.skip

    try:
        for raw_instance in dataset:
            inst = normalize_instance(raw_instance)
            if not should_include_instance(inst, repo_filter=args.repo, tier_filter=args.tier, allow_ids=allowed_ids):
                continue
            if skipped > 0:
                skipped -= 1
                continue

            repo_path: Optional[Path] = None
            if not args.dry_run:
                repo_path = ensure_repo_checkout(
                    inst["repo"],
                    inst.get("base_commit"),
                    repos_dir,
                    repo_cache,
                    created_paths,
                )

            payload = build_instance_payload(inst, repo_path=repo_path, args=args)
            selected.append(payload)
            logger.info("Prepared %s (%d/%s)", payload["instance_id"], len(selected), args.limit or "∞")

            if args.limit is not None and len(selected) >= args.limit:
                break

    finally:
        if not args.keep_repos:
            for path in created_paths:
                try:
                    shutil.rmtree(path)
                except OSError:
                    logger.warning("Failed to remove %s", path)

    if args.dry_run:
        for payload in selected:
            logger.info("[dry-run] would write %s", payload["instance_id"])
        return

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(selected, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %d instances to %s", len(selected), out_path)


if __name__ == "__main__":
    main()
