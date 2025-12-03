"""CLI runner for verification rules."""

import argparse
import importlib
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import List, Optional

from . import RULE_IDS
from .base import RuleResult


def _ensure_project_namespace() -> None:
    """Alias the local package so imports from verifier_harness.* keep working."""
    namespace = "verifier_harness"
    if namespace in sys.modules:
        return

    root_dir = Path(__file__).resolve().parents[2]
    harness_pkg = ModuleType(namespace)
    harness_pkg.__path__ = [str(root_dir)]
    sys.modules[namespace] = harness_pkg

    verifier_mod = importlib.import_module("verifier")
    sys.modules[f"{namespace}.verifier"] = verifier_mod
    sys.modules[f"{namespace}.verifier.rules"] = importlib.import_module("verifier.rules")


def _load_rule(rule_id: str):
    _ensure_project_namespace()
    module_path = f"{__package__}.{rule_id}.rule"
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"Unknown rule module: {module_path}") from exc


def run_rules(rule_ids: List[str], repo_path: str, patch_str: str) -> List[RuleResult]:
    results: List[RuleResult] = []
    for rule_id in rule_ids:
        module = _load_rule(rule_id)
        run_rule = getattr(module, "run_rule", None)
        if not callable(run_rule):  # pragma: no cover - defensive
            raise SystemExit(f"Rule module {rule_id} is missing a run_rule(repo_path, patch_str) function")
        results.append(run_rule(repo_path=repo_path, patch_str=patch_str))
    return results


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run verifier rules against a patch.")
    parser.add_argument("--rule", choices=["all"] + RULE_IDS, default="all", help="Rule to run (default: all)")
    parser.add_argument("--repo", required=True, help="Path to the repository containing the patched code")

    patch_group = parser.add_mutually_exclusive_group(required=True)
    patch_group.add_argument("--patch-file", help="Path to a unified diff patch file")
    patch_group.add_argument("--patch-stdin", action="store_true", help="Read patch contents from stdin")
    return parser.parse_args(argv)


def _read_patch(args: argparse.Namespace) -> str:
    if args.patch_stdin:
        return sys.stdin.read()
    patch_path = Path(args.patch_file)
    return patch_path.read_text(encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    patch_str = _read_patch(args)

    rule_ids = RULE_IDS if args.rule == "all" else [args.rule]
    results = run_rules(rule_ids, repo_path=args.repo, patch_str=patch_str)
    payload = [r.to_dict() for r in results]

    if len(payload) == 1:
        print(json.dumps(payload[0], indent=2))
    else:
        print(json.dumps(payload, indent=2))

    failures = [result for result in results if result.status == "failed"]
    sys.exit(1 if failures else 0)


if __name__ == "__main__":  # pragma: no cover
    main()
