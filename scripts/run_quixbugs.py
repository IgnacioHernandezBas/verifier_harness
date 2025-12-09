#!/usr/bin/env python3
"""
Run the integrated verifier pipeline on QuixBugs programs.

This script pairs each buggy Python implementation from `python_programs/`
with its reference fix in `correct_python_programs/`, generates a unified diff,
and evaluates it through the EvaluationPipeline. A temporary copy of the repo is
created per program so imports resolve exactly as they do in QuixBugs.

Examples:
    python scripts/run_quixbugs.py --programs bitcount mergesort --skip-static --skip-rules
    python scripts/run_quixbugs.py --limit 5 --output results/quixbugs.json
"""

import argparse
import difflib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation_pipeline import EvaluationPipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run verifier pipeline on QuixBugs programs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--quixbugs-root",
        type=Path,
        default=REPO_ROOT / "QuixBugs",
        help="Path to the cloned QuixBugs repository",
    )
    parser.add_argument(
        "--programs",
        nargs="+",
        help="Specific program names (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of programs to evaluate",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save JSON results",
    )
    parser.add_argument(
        "--skip-static",
        action="store_true",
        help="Disable static analysis stage",
    )
    parser.add_argument(
        "--skip-rules",
        action="store_true",
        help="Disable supplementary rules stage",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=0.5,
        help="Coverage threshold applied to the dynamic fuzzing verdict",
    )
    parser.add_argument(
        "--fuzzing-timeout",
        type=int,
        default=120,
        help="Timeout for executing generated tests (seconds)",
    )
    return parser.parse_args()


def list_programs(quixbugs_root: Path) -> List[str]:
    source_dir = quixbugs_root / "python_programs"
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing python_programs directory at {source_dir}")
    return sorted(p.stem for p in source_dir.glob("*.py"))


def load_program_pair(quixbugs_root: Path, program: str) -> Dict[str, str]:
    buggy_path = quixbugs_root / "python_programs" / f"{program}.py"
    patched_path = quixbugs_root / "correct_python_programs" / f"{program}.py"
    if not buggy_path.exists():
        raise FileNotFoundError(f"Buggy file not found: {buggy_path}")
    if not patched_path.exists():
        raise FileNotFoundError(f"Correct file not found: {patched_path}")
    return {
        "buggy": buggy_path.read_text(),
        "patched": patched_path.read_text(),
        "rel_path": f"python_programs/{program}.py",
    }


def build_diff(original: str, patched: str, rel_path: str) -> str:
    diff_lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    return "".join(diff_lines)


def main() -> None:
    args = parse_args()

    quixbugs_root = args.quixbugs_root.resolve()
    if not quixbugs_root.exists():
        raise SystemExit(f"QuixBugs repository not found at {quixbugs_root}")

    available_programs = list_programs(quixbugs_root)
    requested = args.programs if args.programs else available_programs
    unknown = sorted(set(requested) - set(available_programs))
    if unknown:
        raise SystemExit(f"Unknown programs: {', '.join(unknown)}")

    if args.limit:
        requested = requested[: args.limit]

    pipeline = EvaluationPipeline(
        enable_static=not args.skip_static,
        enable_fuzzing=True,
        enable_rules=not args.skip_rules,
        fuzzing_timeout=args.fuzzing_timeout,
        coverage_threshold=args.coverage_threshold,
    )

    results = []
    print(f"Running verifier on {len(requested)} QuixBugs program(s)...\n")

    for program in requested:
        print(f"{'#' * 80}")
        print(f"# Program: {program}")
        print(f"{'#' * 80}")

        pair = load_program_pair(quixbugs_root, program)
        diff = build_diff(pair["buggy"], pair["patched"], pair["rel_path"])

        with tempfile.TemporaryDirectory(prefix=f"quixbugs_eval_{program}_") as tmpdir:
            repo_copy = Path(tmpdir) / "repo"
            shutil.copytree(quixbugs_root, repo_copy, dirs_exist_ok=True)

            target_file = repo_copy / pair["rel_path"]
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(pair["patched"])
            (target_file.parent / "__init__.py").touch(exist_ok=True)

            patch_data = {
                "id": f"quixbugs__{program}",
                "diff": diff,
                "patched_code": pair["patched"],
                "original_code": pair["buggy"],
                "repo_path": str(repo_copy),
            }

            result = pipeline.evaluate_patch(
                patch_data,
                skip_static=args.skip_static,
                skip_fuzzing=False,
                skip_rules=args.skip_rules,
            )
            results.append(result)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2))
        print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()

