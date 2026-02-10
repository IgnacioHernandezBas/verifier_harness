from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from claim_test_generation.claim_test_generator import (
    guess_import_from_path,
    pick_primary_grounding_path,
)


MAX_SOURCE_CHARS = 1200


@dataclass
class GroundingEvidence:
    symbol: Optional[str]
    path: Optional[str]
    line: Optional[int]
    snippet: Optional[str]
    source_excerpt: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IssueContext:
    code_blocks: List[str]
    cli_commands: List[str]
    expected_outputs: List[str]
    tracebacks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolSignature:
    symbol: str
    signature: Optional[str]
    docstring: Optional[str]
    source: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommitDiff:
    base_commit: Optional[str]
    patch_files: List[str]
    test_patch_files: List[str]
    patch_additions: int
    patch_deletions: int
    test_patch_additions: int
    test_patch_deletions: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolSnippet:
    symbol: str
    path: Optional[str]
    line: Optional[int]
    snippet: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FixtureInfo:
    name: str
    path: Optional[str]
    scope: Optional[str]
    params: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimContext:
    instance_id: str
    claim_id: str
    repo: str
    repo_path: Optional[str]
    claim_type: Optional[str]
    claim_text: str
    given: str
    when: str
    then: str
    target_symbols: List[str]
    primary_path: Optional[str]
    primary_module: Optional[str]
    grounding: List[GroundingEvidence]
    issue_context: IssueContext
    confidence: Optional[str]
    computed_score: Optional[int]
    signatures: List[SymbolSignature]
    commit_diff: CommitDiff
    touched_paths: List[str]
    symbol_snippets: List[SymbolSnippet] = field(default_factory=list)
    fixtures: List[FixtureInfo] = field(default_factory=list)
    primary_file_exists: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def serialize_claim_context(context: ClaimContext) -> Dict[str, Any]:
    return context.to_dict()


def deserialize_claim_context(payload: Dict[str, Any]) -> ClaimContext:
    grounding = [
        GroundingEvidence(
            symbol=item.get("symbol"),
            path=item.get("path"),
            line=item.get("line"),
            snippet=item.get("snippet"),
            source_excerpt=item.get("source_excerpt"),
        )
        for item in payload.get("grounding", [])
    ]
    issue_data = payload.get("issue_context") or {}
    issue_ctx = IssueContext(
        code_blocks=list(issue_data.get("code_blocks") or []),
        cli_commands=list(issue_data.get("cli_commands") or []),
        expected_outputs=list(issue_data.get("expected_outputs") or []),
        tracebacks=list(issue_data.get("tracebacks") or []),
    )
    signatures = [
        SymbolSignature(
            symbol=item.get("symbol", ""),
            signature=item.get("signature"),
            docstring=item.get("docstring"),
            source=item.get("source"),
        )
        for item in payload.get("signatures", [])
    ]
    commit_data = payload.get("commit_diff") or {}
    commit_diff = CommitDiff(
        base_commit=commit_data.get("base_commit"),
        patch_files=list(commit_data.get("patch_files") or []),
        test_patch_files=list(commit_data.get("test_patch_files") or []),
        patch_additions=commit_data.get("patch_additions", 0),
        patch_deletions=commit_data.get("patch_deletions", 0),
        test_patch_additions=commit_data.get("test_patch_additions", 0),
        test_patch_deletions=commit_data.get("test_patch_deletions", 0),
    )
    symbol_snippets = [
        SymbolSnippet(
            symbol=item.get("symbol", ""),
            path=item.get("path"),
            line=item.get("line"),
            snippet=item.get("snippet"),
        )
        for item in payload.get("symbol_snippets", [])
    ]
    fixtures = [
        FixtureInfo(
            name=item.get("name", ""),
            path=item.get("path"),
            scope=item.get("scope"),
            params=list(item.get("params") or []),
        )
        for item in payload.get("fixtures", [])
    ]
    return ClaimContext(
        instance_id=payload["instance_id"],
        claim_id=payload["claim_id"],
        repo=payload["repo"],
        repo_path=payload.get("repo_path"),
        claim_type=payload.get("claim_type"),
        claim_text=payload.get("claim_text", ""),
        given=payload.get("given", ""),
        when=payload.get("when", ""),
        then=payload.get("then", ""),
        target_symbols=list(payload.get("target_symbols") or []),
        primary_path=payload.get("primary_path"),
        primary_module=payload.get("primary_module"),
        grounding=grounding,
        issue_context=issue_ctx,
        confidence=payload.get("confidence"),
        computed_score=payload.get("computed_score"),
        signatures=signatures,
        commit_diff=commit_diff,
        touched_paths=list(payload.get("touched_paths") or []),
        symbol_snippets=symbol_snippets,
        fixtures=fixtures,
        primary_file_exists=payload.get("primary_file_exists", True),
    )


def hash_claim_context(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def _clean_str(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip()


def _resolve_repo_root(
    repo_name: str,
    instance_id: Optional[str],
    base_commit: Optional[str],
    repos_root: Optional[Path],
) -> Optional[Path]:
    if not repos_root:
        return None
    slug = repo_name.replace("/", "__")
    candidates: List[Path] = []
    slug_path = repos_root / slug
    inst_path = repos_root / instance_id if instance_id else None
    if base_commit:
        candidates.append(slug_path / base_commit)
        if inst_path is not None:
            candidates.append(inst_path / base_commit)
    candidates.append(slug_path)
    if inst_path is not None:
        candidates.append(inst_path)
    # allow slug with suffix (e.g., repo__instanceid) and commit children
    for extra in sorted(repos_root.glob(f"{slug}*")):
        if base_commit:
            candidates.append(extra / base_commit)
        candidates.append(extra)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_source_excerpt(repo_dir: Optional[Path], rel_path: Optional[str]) -> Optional[str]:
    if not repo_dir or not rel_path:
        return None
    candidate = repo_dir / rel_path
    if not candidate.exists() or not candidate.is_file():
        return None
    try:
        text = candidate.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

    # If text is short enough, return as-is
    if len(text) <= MAX_SOURCE_CHARS:
        return text

    # Smart truncation: try to include complete function/class definitions
    # Look for function/class signatures and extend to include full signature
    truncated = text[:MAX_SOURCE_CHARS]

    # If we're in the middle of a function signature (contains 'def ' or 'class ' but no closing paren)
    import re
    if re.search(r'\b(def|class)\s+\w+\s*\(', truncated) and truncated.count('(') > truncated.count(')'):
        # Try to extend to the closing paren of the signature
        extra_chars = min(500, len(text) - MAX_SOURCE_CHARS)
        extended = text[:MAX_SOURCE_CHARS + extra_chars]
        # Find the first line after the signature starts
        match = re.search(r'(\bdef\b.*?:\s*\n)', extended, re.DOTALL)
        if match:
            return extended[:match.end()]

    return truncated


def _extract_issue_context(
    claim: Dict[str, Any], issue_context: Optional[Dict[str, Any]]
) -> IssueContext:
    if not issue_context:
        return IssueContext(code_blocks=[], cli_commands=[], expected_outputs=[], tracebacks=[])

    refs = claim.get("issue_context_refs") or {}

    def collect(ref_key: str, ctx_key: str, value_key: str) -> List[str]:
        entries = issue_context.get(ctx_key) or []
        ref_ids = refs.get(ref_key)
        if not ref_ids:
            return []
        collected: List[str] = []
        for idx in ref_ids:
            if not isinstance(idx, int):
                continue
            if idx < 0 or idx >= len(entries):
                continue
            entry = entries[idx]
            value = entry.get(value_key) if isinstance(entry, dict) else None
            if not value:
                continue
            collected.append(value.strip())
        return collected

    return IssueContext(
        code_blocks=collect("code_block_ids", "code_blocks", "content"),
        cli_commands=collect("cli_command_ids", "cli_commands", "command"),
        expected_outputs=collect(
            "expected_output_block_ids", "expected_output_blocks", "content"
        ),
        tracebacks=collect("traceback_ids", "tracebacks", "content"),
    )


def _extract_grounding(
    claim: Dict[str, Any], repo_dir: Optional[Path]
) -> List[GroundingEvidence]:
    grounding = claim.get("grounding") or {}
    evidences = grounding.get("evidence") or []
    payload: List[GroundingEvidence] = []
    for item in evidences:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol")
        path = item.get("path")
        line = item.get("line") if isinstance(item.get("line"), int) else None
        snippet = item.get("snippet")
        excerpt = _read_source_excerpt(repo_dir, path)
        payload.append(
            GroundingEvidence(
                symbol=symbol,
                path=path,
                line=line,
                snippet=snippet,
                source_excerpt=excerpt,
            )
        )
    return payload


def _parse_patch_paths(patch: Optional[str]) -> List[str]:
    if not patch:
        return []
    files: List[str] = []
    seen = set()
    for line in patch.splitlines():
        prefix = None
        if line.startswith("+++ b/"):
            prefix = "+++ b/"
        elif line.startswith("--- a/"):
            prefix = "--- a/"
        if prefix:
            path = line[len(prefix) :].strip()
            if not path or path == "/dev/null":
                continue
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _count_patch_stats(patch: Optional[str]) -> tuple[int, int]:
    if not patch:
        return 0, 0
    additions = 0
    deletions = 0
    for line in patch.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return additions, deletions


def _build_commit_diff(sample: Dict[str, Any]) -> CommitDiff:
    patch = sample.get("patch")
    test_patch = sample.get("test_patch")
    patch_files = _parse_patch_paths(patch)
    test_files = _parse_patch_paths(test_patch)
    patch_add, patch_del = _count_patch_stats(patch)
    test_add, test_del = _count_patch_stats(test_patch)
    return CommitDiff(
        base_commit=sample.get("base_commit"),
        patch_files=patch_files,
        test_patch_files=test_files,
        patch_additions=patch_add,
        patch_deletions=patch_del,
        test_patch_additions=test_add,
        test_patch_deletions=test_del,
    )


def _collect_touched_paths(
    primary_path: Optional[str],
    grounding: List[GroundingEvidence],
    commit_diff: CommitDiff,
) -> List[str]:
    seen = set()
    ordered: List[str] = []

    def add(path: Optional[str]) -> None:
        if not path:
            return
        if path in seen:
            return
        seen.add(path)
        ordered.append(path)

    add(primary_path)
    for evidence in grounding:
        add(evidence.path)
    for path in commit_diff.patch_files:
        add(path)
    for path in commit_diff.test_patch_files:
        add(path)
    return ordered


def _load_module_from_repo(module_name: Optional[str], repo_dir: Optional[Path]):
    if not module_name:
        return None
    inserted = False
    repo_str = str(repo_dir) if repo_dir else None
    if repo_str:
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)
            inserted = True
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None
    finally:
        if inserted and repo_str:
            try:
                sys.path.remove(repo_str)
            except ValueError:
                pass


def _collect_symbol_signatures(
    module_name: Optional[str], symbols: List[str], repo_dir: Optional[Path]
) -> List[SymbolSignature]:
    if not module_name or not symbols:
        return []
    module = _load_module_from_repo(module_name, repo_dir)
    if module is None:
        return []
    payload: List[SymbolSignature] = []
    for symbol in symbols:
        attr = getattr(module, symbol, None)
        if attr is None:
            continue
        signature = None
        try:
            signature = f"{symbol}{inspect.signature(attr)}"
        except (ValueError, TypeError):
            signature = None
        doc = inspect.getdoc(attr)
        try:
            source = inspect.getsource(attr)
            if len(source) > MAX_SOURCE_CHARS:
                source = source[: MAX_SOURCE_CHARS - 1] + "…"
        except (OSError, TypeError):
            source = None
        payload.append(
            SymbolSignature(
                symbol=symbol,
                signature=signature,
                docstring=doc,
                source=source,
            )
        )
    return payload


def build_claim_context(
    *,
    claim: Dict[str, Any],
    sample: Dict[str, Any],
    issue_context: Optional[Dict[str, Any]],
    repos_root: Optional[Path] = None,
) -> ClaimContext:
    repo_name = sample.get("repo", "unknown_repo")
    instance_id = sample.get("instance_id") or sample.get("metadata", {}).get("instance_id")
    claim_id = claim.get("claim_id") or "C1"
    primary_path = pick_primary_grounding_path(claim)
    primary_module = guess_import_from_path(primary_path)
    base_commit = sample.get("base_commit")
    repo_dir = _resolve_repo_root(repo_name, instance_id, base_commit, repos_root)

    grounding = _extract_grounding(claim, repo_dir)
    issue_ctx = _extract_issue_context(claim, issue_context)
    commit_diff = _build_commit_diff(sample)
    signatures = _collect_symbol_signatures(primary_module, claim.get("target_symbols") or [], repo_dir)
    touched_paths = _collect_touched_paths(primary_path, grounding, commit_diff)

    return ClaimContext(
        instance_id=instance_id or "unknown_instance",
        claim_id=claim_id,
        repo=repo_name,
        repo_path=str(repo_dir) if repo_dir else None,
        claim_type=claim.get("claim_type"),
        claim_text=_clean_str(claim.get("claim_text")),
        given=_clean_str(claim.get("given")),
        when=_clean_str(claim.get("when")),
        then=_clean_str(claim.get("then")),
        target_symbols=list(claim.get("target_symbols") or []),
        primary_path=primary_path,
        primary_module=primary_module,
        grounding=grounding,
        issue_context=issue_ctx,
        confidence=claim.get("confidence"),
        computed_score=claim.get("computed_score"),
        signatures=signatures,
        commit_diff=commit_diff,
        touched_paths=touched_paths,
        primary_file_exists=bool(
            repo_dir and primary_path and (repo_dir / primary_path).exists()
        ),
    )
