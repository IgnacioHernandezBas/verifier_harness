from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .context import ClaimContext, FixtureInfo, SymbolSnippet


@dataclass
class GatheringResult:
    repo_dir: Optional[Path]
    primary_file_exists: bool


def enrich_claim_context(context: ClaimContext, repos_root: Optional[Path]) -> ClaimContext:
    repo_dir = _resolve_repo_dir(context, repos_root)
    primary_exists = _check_primary_file(repo_dir, context.primary_path)
    context.primary_file_exists = primary_exists
    if repo_dir:
        context.repo_path = str(repo_dir)
    context.symbol_snippets = _collect_symbol_snippets(
        repo_dir=repo_dir,
        symbols=context.target_symbols,
        max_matches=4,
    )
    context.fixtures = _collect_fixtures(repo_dir)
    return context


def _resolve_repo_dir(context: ClaimContext, repos_root: Optional[Path]) -> Optional[Path]:
    if context.repo_path:
        repo_path = Path(context.repo_path)
        if repo_path.exists():
            return repo_path
    if not repos_root:
        return None
    slug = context.repo.replace("/", "__")
    candidates: List[Path] = []
    candidates.append(repos_root / slug)
    candidates.append(repos_root / context.instance_id)
    candidates.extend(sorted(repos_root.glob(f"{slug}*")))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _check_primary_file(repo_dir: Optional[Path], primary_path: Optional[str]) -> bool:
    if not repo_dir or not primary_path:
        return False
    candidate = repo_dir / primary_path
    return candidate.exists()


def _collect_symbol_snippets(
    repo_dir: Optional[Path],
    symbols: Iterable[str],
    *,
    max_matches: int,
) -> List[SymbolSnippet]:
    if not repo_dir:
        return []
    snippets: List[SymbolSnippet] = []
    for symbol in symbols:
        pattern = rf"(def|class)\s+{symbol}\b"
        matches = _run_rg(pattern, repo_dir, max_matches=max_matches)
        if not matches:
            continue
        for path, line in matches:
            snippet = _read_snippet(repo_dir / path, line)
            snippets.append(
                SymbolSnippet(
                    symbol=symbol,
                    path=str(path),
                    line=line,
                    snippet=snippet,
                )
            )
    return snippets


def _run_rg(pattern: str, repo_dir: Path, *, max_matches: int) -> List[Tuple[Path, int]]:
    try:
        completed = subprocess.run(
            [
                "rg",
                "-n",
                "-m",
                str(max_matches),
                pattern,
                str(repo_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    matches: List[Tuple[Path, int]] = []
    for line in completed.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        path_str, line_no = parts[0], parts[1]
        try:
            rel_path = Path(path_str).relative_to(repo_dir)
        except ValueError:
            rel_path = Path(path_str)
        try:
            line_num = int(line_no)
        except ValueError:
            continue
        matches.append((rel_path, line_num))
    return matches


def _read_snippet(file_path: Path, line_no: int, *, context: int = 3) -> Optional[str]:
    if not file_path.exists():
        return None
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return None
    start = max(line_no - context - 1, 0)
    end = min(line_no + context, len(lines))
    excerpt = lines[start:end]
    numbered = [
        f"{start + idx + 1}: {text}" for idx, text in enumerate(excerpt)
    ]
    return "\n".join(numbered)


def _collect_fixtures(repo_dir: Optional[Path]) -> List[FixtureInfo]:
    """
    Collect pytest fixtures from repository.

    DISABLED: Repository-specific fixtures are not available when tests run in isolation.
    Generated tests must be self-contained and only use standard pytest built-in fixtures
    (tmp_path, monkeypatch, capsys, etc.).

    If you need to re-enable fixture collection in the future, ensure tests are run
    within the repository's test directory where conftest.py files are loaded.
    """
    # Return empty list to prevent LLM from trying to use unavailable fixtures
    return []

    # Original implementation (disabled):
    # if not repo_dir:
    #     return []
    # candidates = list(repo_dir.rglob("conftest.py"))
    # tests_dir = repo_dir / "tests"
    # if tests_dir.exists():
    #     candidates.extend(tests_dir.rglob("*.py"))
    #
    # fixtures: List[FixtureInfo] = []
    # seen = set()
    # for path in candidates:
    #     fixtures.extend(_extract_fixtures_from_file(path, repo_dir, seen))
    # return fixtures


def _extract_fixtures_from_file(
    file_path: Path, repo_dir: Path, seen: set
) -> List[FixtureInfo]:
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    rel_path = str(file_path.relative_to(repo_dir))
    fixtures: List[FixtureInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info = _fixture_info_from_node(node)
            if not info:
                continue
            key = (info.name, rel_path)
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(
                FixtureInfo(
                    name=info.name,
                    path=rel_path,
                    scope=info.scope,
                    params=info.params,
                )
            )
    return fixtures


def _fixture_info_from_node(node: ast.AST) -> Optional["FixtureMeta"]:
    decorators = getattr(node, "decorator_list", [])
    for decorator in decorators:
        call = decorator
        if isinstance(decorator, ast.Call):
            target = decorator.func
        else:
            target = decorator
        if not _is_fixture_target(target):
            continue
        scope = None
        params: List[str] = []
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == "scope":
                    scope = _literal_eval_str(keyword.value)
                if keyword.arg == "params":
                    params = _literal_eval_list(keyword.value)
        name = getattr(node, "name", None)
        if not name:
            return None
        return FixtureMeta(name=name, scope=scope, params=params)
    return None


def _is_fixture_target(target: ast.AST) -> bool:
    if isinstance(target, ast.Attribute):
        return target.attr == "fixture"
    if isinstance(target, ast.Name):
        return target.id == "fixture"
    return False


def _literal_eval_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_eval_list(node: ast.AST) -> List[str]:
    if isinstance(node, ast.List):
        values: List[str] = []
        for elt in node.elts:
            value = _literal_eval_str(elt)
            if value is not None:
                values.append(value)
        return values
    return []


@dataclass
class FixtureMeta:
    name: str
    scope: Optional[str]
    params: List[str]
