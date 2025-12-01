import difflib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
# Ensure the repository root is importable so `verifier_harness` resolves when
# tests are run from within the `verifier_harness` directory.
for candidate in (PROJECT_ROOT, ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


def write_file(base: Path, relative: str, content: str) -> Path:
    target = base / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def make_patch(old: str, new: str, path: str) -> str:
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return "\n".join(diff) + "\n"


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def run_rule() -> Callable[[str, Path, str], object]:
    def _run(rule_id: str, repo_path: Path, patch_str: str):
        module = importlib.import_module(f"verifier_harness.verifier.rules.{rule_id}.rule")
        return module.run_rule(repo_path=str(repo_path), patch_str=patch_str)

    return _run


@pytest.fixture
def run_cli(tmp_path: Path):
    def _run(rule_id: str, repo_path: Path, patch_str: str):
        patch_file = tmp_path / "patch.diff"
        patch_file.write_text(patch_str, encoding="utf-8")
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        entries = [str(PROJECT_ROOT)]
        if pythonpath:
            entries.append(pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(entries)

        cmd = [
            sys.executable,
            "-m",
            "verifier_harness.verifier.rules.runner",
            "--rule",
            rule_id,
            "--repo",
            str(repo_path),
            "--patch-file",
            str(patch_file),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return completed

    return _run
