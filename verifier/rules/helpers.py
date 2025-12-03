"""Shared helper utilities for rule implementations."""

import ast
import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

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
    current_file: Optional[str] = None
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


def is_documentation_only_patch(patch_str: str) -> bool:
    """
    Determine if a patch only modifies documentation/comments.

    Returns True if the patch appears to only change:
    - Docstrings (triple-quoted strings)
    - Comments (lines starting with #)
    - Whitespace/formatting
    - Documentation files (.md, .rst, .txt)

    Returns False if it modifies executable Python code.
    """
    patch_data = parse_patch_by_file(patch_str)

    for file_path, changes in patch_data.items():
        # Check if it's a documentation file
        if file_path.endswith(('.md', '.rst', '.txt', '.html', '.xml')):
            continue

        # For Python files, check if changes are code or docs
        if file_path.endswith('.py'):
            all_lines = changes['added'] + changes['removed']

            for line in all_lines:
                stripped = line.strip()

                # Skip empty lines
                if not stripped:
                    continue

                # Skip comment lines
                if stripped.startswith('#'):
                    continue

                # Skip docstring markers and content (basic heuristic)
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if '"""' in stripped or "'''" in stripped:
                    continue

                # Skip lines that look like docstring content
                # (indented text without code-like syntax)
                if not any(char in stripped for char in ['=', '(', ')', '[', ']', '{', '}', 'def ', 'class ', 'import ', 'from ', 'return ', 'if ', 'for ', 'while ']):
                    # Likely docstring content
                    continue

                # If we get here, it's likely executable code
                return False

    return True


def _load_module_from_path(path: Path, repo_root: Optional[Path] = None):
    """
    Load a module from a file path.

    If repo_root is provided and the path is within it, the module will be loaded
    using proper package imports to support relative imports.
    """
    # Check if path is under repo_root (Python 3.6 compatible)
    if repo_root:
        try:
            rel_path = path.relative_to(repo_root)
            is_under_repo = True
        except ValueError:
            is_under_repo = False
    else:
        is_under_repo = False

    if is_under_repo:
        # Convert file path to module name (e.g., sklearn/linear_model/ridge.py -> sklearn.linear_model.ridge)
        module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]  # Remove .py extension
        module_name = '.'.join(module_parts)

        # Add repo root to sys.path temporarily
        repo_root_str = str(repo_root)
        path_added = False
        if repo_root_str not in sys.path:
            sys.path.insert(0, repo_root_str)
            path_added = True

        try:
            # Use regular import which handles packages correctly
            module = importlib.import_module(module_name)
            return module
        finally:
            # Clean up sys.path if we added it
            if path_added and repo_root_str in sys.path:
                sys.path.remove(repo_root_str)
    else:
        # Load as standalone module (no relative imports supported)
        module_name = f"rule_module_{hash(path)}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise ImportError(f"Cannot load module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def load_module_from_repo(repo_path: str, rel_path: str):
    """
    Load a Python module from the repository given a relative path.

    Returns None if the module cannot be loaded (e.g., missing file or import error).
    """
    file_path = Path(repo_path) / rel_path
    if not file_path.exists():
        return None
    repo_root = Path(repo_path)
    try:
        return _load_module_from_path(file_path, repo_root=repo_root)
    except (ImportError, Exception):
        # Cannot import module (e.g., C extension incompatibility)
        return None


def _compute_end_lineno(node: ast.AST) -> int:
    """
    Compute the end line number for an AST node.

    In Python 3.8+, nodes have end_lineno. For older versions, we compute it
    by finding the maximum line number in the node's subtree.
    """
    if hasattr(node, 'end_lineno') and node.end_lineno is not None:
        return node.end_lineno

    # Fallback for Python < 3.8: find max lineno in subtree
    max_lineno = node.lineno if hasattr(node, 'lineno') else 0
    for child in ast.walk(node):
        if hasattr(child, 'lineno') and child.lineno is not None:
            max_lineno = max(max_lineno, child.lineno)
    return max_lineno


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
    """
    Load callables for functions touched by the diff.

    Note: If a module cannot be imported (e.g., C extension incompatibility),
    it will be skipped. Returns an empty list if no functions can be loaded.
    """
    diff_info = parse_unified_diff(patch_str)
    paths = filter_paths_to_py(list(diff_info.keys()))
    functions: List[FunctionInfo] = []
    repo_root = Path(repo_path)

    for rel_path in paths:
        ranges = diff_info.get(rel_path, [])
        file_path = repo_root / rel_path
        if not file_path.exists():
            continue

        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Try to load the module to get callable functions
        # If import fails (e.g., C extension incompatibility), skip this file
        try:
            module = _load_module_from_path(file_path, repo_root=repo_root)
        except (ImportError, Exception):
            # Cannot import module - skip function execution checks
            # Rules can still do static analysis on the AST
            continue

        for node in _iter_function_defs(tree):
            end_lineno = _compute_end_lineno(node)
            if _line_overlaps(ranges, node.lineno, end_lineno):
                func = getattr(module, node.name, None)
                if callable(func):
                    # Verify this is actually an inspectable function/method
                    # Skip method-wrappers, built-ins, and other non-inspectable callables
                    import inspect
                    if not (inspect.isfunction(func) or inspect.ismethod(func)):
                        continue
                    # Try to get source to ensure it's inspectable
                    try:
                        inspect.getsource(func)
                    except (OSError, TypeError):
                        # Cannot get source - skip this function
                        continue

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
