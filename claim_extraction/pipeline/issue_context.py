# claim_extraction/pipeline/issue_context.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple


_CODE_BLOCK_RE = re.compile(r"```(\w+)?\s*\n([\s\S]*?)```", re.MULTILINE)
_INLINE_TICKS_RE = re.compile(r"`([^`]+)`")
_CLI_LINE_RE = re.compile(r"(?m)^[ \t]*[$>]\s*(.+)$")
_TRACEBACK_RE = re.compile(
    r"Traceback \(most recent call last\):[\s\S]*?(?=\n\s*\n|$)",
    re.IGNORECASE,
)

_EXPECTED_HEADINGS = (
    "expected behavior",
    "expected behaviour",
    "expected result",
    "actual behavior",
    "actual behaviour",
    "actual result",
    "observed behavior",
    "observed result",
)
_EXPECTED_HEADING_RE = re.compile(
    r"(?im)^(?:" + "|".join(re.escape(h) for h in _EXPECTED_HEADINGS) + r")\s*:?.*$"
)

_CLI_KEYWORDS = (
    "pylint",
    "pytest",
    "python -m",
    "python3 -m",
    "pip",
    "conda",
    "tox",
    "flake8",
    "mypy",
    "uv",
    "hatch",
)

_OUTPUT_MARKERS = re.compile(r"(W\d{4}|E\d{4}|\*{5,}|Expected behavior|Actual behavior)", re.IGNORECASE)

_SYMBOL_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b")
_PATH_RE = re.compile(r"\b[\w./-]+\.py\b")
_OPTION_RE = re.compile(r"--[A-Za-z0-9][\w-]*(?:=[^\s`]+)?")

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\.]{2,}")


def build_issue_context(problem_statement: str) -> Dict[str, Any]:
    text = problem_statement or ""

    code_blocks = _extract_code_blocks(text)
    cli_commands = _extract_cli_commands(text)
    expected_output_blocks = _extract_expected_outputs(text)

    # --- Tracebacks: extract globally + also from code blocks (robust) ---
    tracebacks = _extract_tracebacks(text)
    for blk in code_blocks:
        tracebacks.extend(_extract_tracebacks(blk.get("content", "")))

    tracebacks = _dedup_tracebacks(tracebacks)

    inline_refs = _extract_inline_refs(text)

    return {
        "code_blocks": code_blocks,
        "cli_commands": cli_commands,
        "expected_output_blocks": expected_output_blocks,
        "tracebacks": tracebacks,
        "inline_code_refs": inline_refs,
    }


def link_claim_to_issue_context(claim: Dict[str, Any], issue_context: Dict[str, Any]) -> Dict[str, List[int]]:
    refs = {
        "cli_command_ids": [],
        "expected_output_block_ids": [],
        "code_block_ids": [],
        "traceback_ids": [],
    }
    if not issue_context:
        return refs

    spans = _collect_spans_for_claim(claim) or []

    cli_candidates = issue_context.get("cli_commands", []) or []
    output_blocks = issue_context.get("expected_output_blocks", []) or []
    code_blocks = issue_context.get("code_blocks", []) or []
    tracebacks = issue_context.get("tracebacks", []) or []

    # --- Primary linking: spans-driven ---
    for raw_span in spans:
        span = _normalize_span(raw_span)
        if not span:
            continue

        if _looks_like_command(span):
            _match_entries(span, cli_candidates, "command", refs["cli_command_ids"])

        if _looks_like_output(span):
            _match_entries(span, output_blocks, "content", refs["expected_output_block_ids"])

        if _looks_like_code(span):
            _match_entries(span, code_blocks, "content", refs["code_block_ids"])

        if "traceback" in span.lower():
            _match_entries(span, tracebacks, "content", refs["traceback_ids"])

    # --- Fallback linking: anchor-driven (stricter) ---
    target_symbols = [s for s in (claim.get("target_symbols") or []) if isinstance(s, str) and s.strip()]
    when = (claim.get("when") or "")
    claim_text = (claim.get("claim_text") or "")

    anchors: List[str] = []
    anchors.extend(target_symbols)

    if isinstance(when, str) and when.strip():
        anchors.append(when.strip())
        anchors.extend(_extract_anchor_tokens(when))

    if isinstance(claim_text, str) and claim_text.strip():
        anchors.extend(_extract_anchor_tokens(claim_text))

    anchors = [a for a in {a.strip() for a in anchors if a and isinstance(a, str)} if len(a) >= 3]

    # Only fallback-link code blocks if we haven't linked any already
    if anchors and not refs["code_block_ids"]:
        for i, blk in enumerate(code_blocks):
            content = (blk.get("content") or "")
            if not content:
                continue

            hay = content.lower()
            symbol_matches = sum(1 for s in target_symbols if s.lower() in hay)
            total_matches = sum(1 for a in anchors if a.lower() in hay)

            # Stricter rule:
            # - Prefer at least 1 target_symbol match
            # - Otherwise require >=2 anchor matches
            if symbol_matches >= 1 or total_matches >= 2:
                refs["code_block_ids"].append(i)

    # --- Traceback linking: match tracebacks to linked code blocks (no "add all") ---
    if refs["code_block_ids"] and tracebacks and not refs["traceback_ids"]:
        linked_contents = [ (code_blocks[i].get("content") or "").lower() for i in refs["code_block_ids"] ]
        for tb_i, tb in enumerate(tracebacks):
            tb_content = (tb.get("content") or "").strip()
            if not tb_content:
                continue
            tb_norm = tb_content.lower()

            # Use a short prefix to avoid huge substring checks
            prefix = tb_norm[:200]
            if any(prefix in lc for lc in linked_contents):
                refs["traceback_ids"].append(tb_i)
                continue

            # Fallback: if both contain traceback marker, try a weaker match
            if "traceback (most recent call last):" in tb_norm and any("traceback (most recent call last):" in lc for lc in linked_contents):
                refs["traceback_ids"].append(tb_i)

    # stable order + unique
    for key in refs:
        refs[key] = sorted(set(refs[key]))
    return refs


def _extract_anchor_tokens(text: str) -> List[str]:
    toks = _TOKEN_RE.findall(text or "")
    seen = set()
    out: List[str] = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= 20:
            break
    return out


def _extract_code_blocks(text: str) -> List[Dict[str, Any]]:
    items: List[Tuple[int, Dict[str, Any]]] = []
    for match in _CODE_BLOCK_RE.finditer(text):
        lang = (match.group(1) or "text").lower()
        content = match.group(2).rstrip("\n")
        items.append(
            (
                match.start(),
                {
                    "lang": lang,
                    "content": content,
                    "source": "fenced",
                    "span": {"start": match.start(), "end": match.end()},
                },
            )
        )
    items.sort(key=lambda x: x[0])
    return [item for _, item in items]


def _extract_cli_commands(text: str) -> List[Dict[str, Any]]:
    entries: List[Tuple[int, Dict[str, Any]]] = []
    seen: set[str] = set()

    for match in _INLINE_TICKS_RE.finditer(text):
        command = match.group(1).strip()
        if not command:
            continue
        if not _looks_like_command(command):
            continue
        key = command.lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            (
                match.start(),
                {
                    "command": command,
                    "span": {"start": match.start(), "end": match.end()},
                },
            )
        )

    for match in _CLI_LINE_RE.finditer(text):
        command = match.group(1).strip()
        if not command:
            continue
        key = command.lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            (
                match.start(),
                {
                    "command": command,
                    "span": {"start": match.start(), "end": match.end()},
                },
            )
        )

    entries.sort(key=lambda x: x[0])
    return [entry for _, entry in entries]


def _extract_expected_outputs(text: str) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for heading_match in _EXPECTED_HEADING_RE.finditer(text):
        block = _capture_output_block(text, heading_match.end())
        if not block:
            continue
        blocks.append(block)
    return blocks


def _capture_output_block(text: str, start_idx: int) -> Optional[Dict[str, Any]]:
    idx = start_idx
    length = len(text)
    while idx < length and text[idx] in "\r\n ":
        idx += 1
    if idx >= length:
        return None

    if text.startswith("```", idx):
        match = _CODE_BLOCK_RE.match(text, idx)
        if match:
            return {
                "content": match.group(2).rstrip("\n"),
                "span": {"start": match.start(), "end": match.end()},
            }

    # fallback: capture until blank line or next heading
    end = idx
    while end < length:
        if text[end] == "\n" and end + 1 < length and text[end + 1] == "\n":
            break
        # clearer + more efficient than slicing
        if _EXPECTED_HEADING_RE.match(text, end):
            break
        end += 1

    snippet = text[idx:end].strip()
    if not snippet:
        return None
    return {
        "content": snippet,
        "span": {"start": idx, "end": idx + len(snippet)},
    }


def _extract_tracebacks(text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for match in _TRACEBACK_RE.finditer(text or ""):
        snippet = match.group(0).rstrip()
        if not snippet:
            continue
        items.append(
            {
                "content": snippet,
                "span": {"start": match.start(), "end": match.end()},
            }
        )
    return items


def _dedup_tracebacks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate by normalized content prefix to avoid duplicates from global+codeblock extraction."""
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        content = (it.get("content") or "").strip()
        if not content:
            continue
        key = re.sub(r"\s+", " ", content.lower())[:400]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _extract_inline_refs(text: str) -> Dict[str, List[str]]:
    symbols = _collect_unique_matches(_SYMBOL_RE, text)
    paths = _collect_unique_matches(_PATH_RE, text)
    options = _collect_unique_matches(_OPTION_RE, text)
    return {
        "symbols": symbols,
        "paths": paths,
        "options": options,
    }


def _collect_unique_matches(pattern: re.Pattern[str], text: str) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for match in pattern.finditer(text or ""):
        value = match.group(0)
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


def _collect_spans_for_claim(claim: Dict[str, Any]) -> List[str]:
    spans = ((claim.get("evidence") or {}).get("spans") or [])
    valid_spans = [s for s in spans if isinstance(s, str) and s.strip()]
    if valid_spans:
        return valid_spans

    fields = [claim.get("claim_text"), claim.get("given"), claim.get("when"), claim.get("then")]
    fallback = " ".join(f for f in fields if isinstance(f, str) and f.strip()).strip()
    return [fallback] if fallback else []


def _normalize_span(span: str) -> str:
    stripped = (span or "").strip().strip('`"')
    return re.sub(r"\s+", " ", stripped)


def _looks_like_command(text: str) -> bool:
    lower = (text or "").lower()
    if any(kw in lower for kw in _CLI_KEYWORDS):
        return True
    return bool(re.match(r"^(python|pip|pytest|pylint|conda|tox|flake8|mypy)\b", lower))


def _looks_like_output(text: str) -> bool:
    t = text or ""
    return bool(_OUTPUT_MARKERS.search(t)) or "output" in t.lower()


def _looks_like_code(text: str) -> bool:
    t = text or ""
    return "\n" in t or t.strip().startswith(("def ", "class ")) or ("(" in t and ")" in t)


def _match_entries(span: str, entries: Sequence[Dict[str, Any]], field: str, acc: List[int]) -> None:
    span_norm = (span or "").lower()
    span_tokens = _tokenize(span_norm)
    if not span_tokens:
        return

    for idx, entry in enumerate(entries):
        target = entry.get(field)
        if not isinstance(target, str):
            continue
        target_norm = target.lower()

        if span_norm in target_norm or target_norm in span_norm:
            acc.append(idx)
            continue

        target_tokens = _tokenize(target_norm)
        if not target_tokens:
            continue

        overlap = len(span_tokens & target_tokens) / max(1, len(span_tokens))
        if overlap >= 0.6:
            acc.append(idx)


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.split(r"[^a-z0-9_]+", (text or "").lower()) if tok}
