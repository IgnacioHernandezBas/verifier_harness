#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import py_compile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .claim_test_generator import VLLMClient, generate_pytest_for_claim
from common.model_paths import ModelPaths, MultiModelPaths


def parse_args() -> argparse.Namespace:
    default_endpoint = os.getenv("CLAIM_LLM_ENDPOINT", "http://127.0.0.1:8000/v1")
    default_model = os.getenv("CLAIM_LLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ")
    default_api_key = os.getenv("CLAIM_LLM_API_KEY")

    ap = argparse.ArgumentParser(description="Generate pytest tests from grounded claims.")
    ap.add_argument(
        "--claims_dir",
        help="Directory containing claim JSON files (overrides --claims_model).",
    )
    ap.add_argument(
        "--out_dir",
        help="Directory for generated tests (overrides --model).",
    )
    ap.add_argument(
        "--claims_model",
        help="Model used for claim extraction (determines claims input directory).",
    )
    ap.add_argument("--endpoint", default=default_endpoint, help="LLM HTTP endpoint.")
    ap.add_argument("--model", default=default_model, help="LLM model identifier for test generation.")
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--timeout_s", type=int, default=120)
    ap.add_argument("--max_claims_per_instance", type=int, default=6)
    ap.add_argument("--api_key", default=default_api_key, help="Bearer token (defaults to CLAIM_LLM_API_KEY).")
    ap.add_argument("--dry_run", action="store_true", help="List work without hitting the LLM.")
    ap.add_argument(
        "--use_model_subdirs",
        action="store_true",
        default=True,
        help="Use model-specific subdirectories (default: True).",
    )
    ap.add_argument(
        "--no_model_subdirs",
        action="store_false",
        dest="use_model_subdirs",
        help="Use legacy flat directory structure.",
    )
    return ap.parse_args()


def iter_claim_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.json"):
        if path.is_file():
            yield path


def load_claim_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[WARN] Failed to read {path}: {exc}")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        return None
    return data


def ensure_import_and_function(code: str, claim_id: str) -> str:
    if "import pytest" not in code:
        code = "import pytest\n\n" + code
    slug = _sanitize(claim_id)
    if f"def test_claim_{slug}" not in code:
        code += f"\n\ndef test_claim_{slug}():\n    pytest.skip('LLM did not return a valid test.')\n"
    return code


def main() -> None:
    args = parse_args()

    # Determine paths using ModelPaths or explicit directories
    if args.claims_dir and args.out_dir:
        # Legacy mode: explicit directories provided
        claims_dir = Path(args.claims_dir).resolve()
        out_dir = Path(args.out_dir).resolve()
    else:
        # New mode: use ModelPaths
        if not args.claims_model:
            # If no claims_model specified, use the test generation model
            claims_model = args.model
        else:
            claims_model = args.claims_model

        paths = MultiModelPaths(
            claims_model=claims_model,
            tests_model=args.model,
            use_model_subdirs=args.use_model_subdirs,
        )
        claims_dir = paths.claims_dir()
        out_dir = paths.tests_root()

    if args.dry_run:
        print("[DRY RUN] No files will be generated.")
        print(f"[DRY RUN] Claims directory: {claims_dir}")
        print(f"[DRY RUN] Output directory: {out_dir}")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "total_instances": 0,
        "total_claims": 0,
        "written": 0,
        "compiled_ok": 0,
        "compiled_fail": 0,
        "items": [],
    }
    instances_seen: set[str] = set()

    client = None if args.dry_run else VLLMClient(
        endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout_s,
        api_key=args.api_key,
    )

    for json_path in iter_claim_files(claims_dir):
        data = load_claim_file(json_path)
        if not data:
            continue

        claims = data.get("claims") or []
        if not claims:
            continue

        instance_id = data.get("instance_id") or json_path.stem
        repo = data.get("repo") or "unknown_repo"
        instances_seen.add(instance_id)

        limited_claims = claims[: args.max_claims_per_instance]
        summary["total_claims"] += len(limited_claims)

        instance_dir = out_dir / instance_id
        if not args.dry_run:
            instance_dir.mkdir(parents=True, exist_ok=True)

        for claim in limited_claims:
            claim_id = claim.get("claim_id") or "c1"
            if args.dry_run:
                print(f"[DRY RUN] Would generate test for {instance_id}:{claim_id} ({json_path})")
                continue

            code = generate_pytest_for_claim(
                claim,
                repo=repo,
                instance_id=instance_id,
                client=client,  # type: ignore[arg-type]
            )
            code = ensure_import_and_function(code, claim_id)

            claim_slug = _sanitize(claim_id)
            instance_slug = _sanitize(instance_id)
            file_path = instance_dir / f"{instance_slug}__test_claim_{claim_slug}.py"
            file_path.write_text(code, encoding="utf-8")
            summary["written"] += 1

            compile_ok = True
            error_msg = ""
            try:
                py_compile.compile(str(file_path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_ok = False
                error_msg = str(exc)

            if compile_ok:
                summary["compiled_ok"] += 1
            else:
                summary["compiled_fail"] += 1

            summary["items"].append(
                {
                    "instance_id": instance_id,
                    "claim_id": claim_id,
                    "path": str(file_path),
                    "compile_ok": compile_ok,
                    "error": error_msg,
                }
            )

    summary["total_instances"] = len(instances_seen)

    if args.dry_run:
        print("[DRY RUN] Summary not written.")
    else:
        summary_path = out_dir / "summary_test_generation.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[INFO] Wrote summary to {summary_path}")


def _sanitize(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value).lower()


if __name__ == "__main__":
    main()
