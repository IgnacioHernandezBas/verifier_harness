"""Shared helper utilities for rule implementations."""

from __future__ import annotations

import ast
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple

from verifier_harness.verifier.utils.diff_utils import filter_paths_to_py, parse_unified_diff


@dataclass
class FunctionInfo:
    path: str
    name: str
    lineno: int
    end_lineno: int
    func: Callable[..., Any]


def parse_patch_by_file(patch_str: str) -> Dict[str, Dict[str, List[str]]]:
    """Collect added and removed lines for each file in a patch."""
    data: Dict[str, Dict[str, List[str]]] = {}
    current_file: str | None = None
    for line in patch_str.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            current_file = path
            data.setdefault(path, {"added": [], "removed": []})
            continue
        if current_file is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            data[current_file]["added"].append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            data[current_file]["removed"].append(line[1:])
    return data


def _load_module_from_path(path: Path):
    module_name = f"rule_module_{hash(path)}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module_from_repo(repo_path: str, rel_path: str):
    """Load a Python module from the repository given a relative path."""
    file_path = Path(repo_path) / rel_path
    if not file_path.exists():
        return None
    return _load_module_from_path(file_path)


def _iter_function_defs(tree: ast.AST) -> Iterable[ast.FunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            yield node


def _line_overlaps(ranges: List[Tuple[int, int]], start: int, end: int) -> bool:
    for r_start, r_end in ranges:
        if r_start <= end and start <= r_end:
            return True
    return False


def gather_changed_functions(repo_path: str, patch_str: str) -> List[FunctionInfo]:
    """Load callables for functions touched by the diff."""
    diff_info = parse_unified_diff(patch_str)
    paths = filter_paths_to_py(list(diff_info.keys()))
    functions: List[FunctionInfo] = []

    for rel_path in paths:
        ranges = diff_info.get(rel_path, [])
        file_path = Path(repo_path) / rel_path
        if not file_path.exists():
            continue
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        module = _load_module_from_path(file_path)
        for node in _iter_function_defs(tree):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            if _line_overlaps(ranges, node.lineno, end_lineno):
                func = getattr(module, node.name, None)
                if callable(func):
                    functions.append(
                        FunctionInfo(
                            path=rel_path,
                            name=node.name,
                            lineno=node.lineno,
                            end_lineno=end_lineno,
                            func=func,
                        )
                    )
    return functions
