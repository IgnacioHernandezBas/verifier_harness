# claim_extraction/pipeline/grounding.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Literal


GroundingStatus = Literal["strong", "weak_file", "weak_ref", "none"]


# ----------------------------
# Normalization helpers
# ----------------------------

_BUILTIN_NOISE = {
    "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "print", "sum", "min", "max", "sorted", "range", "enumerate", "zip",
}

def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()

def _snake_to_camel(name: str) -> str:
    if "_" not in name:
        return name
    return "".join(part.capitalize() for part in name.split("_") if part)

def normalize_symbol(symbol: str) -> Set[str]:
    """
    Generate flexible but controlled variants for matching.

    Examples:
    - "Class.method" -> {"Class.method","Class","method","class_method","ClassMethod"}
    - "self.attr" -> {"self.attr","attr"}
    - "FooBar" <-> "foo_bar"
    """
    symbol = (symbol or "").strip()
    if not symbol:
        return set()

    variants: Set[str] = {symbol}

    # dotted
    if "." in symbol:
        parts = [p for p in symbol.split(".") if p]
        variants.update(parts)
        if parts and parts[0] in ("self", "cls") and len(parts) >= 2:
            variants.add(parts[1])

    # identifier camel<->snake
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", symbol):
        variants.add(_camel_to_snake(symbol))
        variants.add(_snake_to_camel(symbol))

    # camel/snake per dotted part
    for v in list(variants):
        if "." in v:
            for p in v.split("."):
                if p:
                    variants.add(_camel_to_snake(p))
                    variants.add(_snake_to_camel(p))

    return {v for v in variants if v}


# ----------------------------
# Diff parsing with line numbers (auditable evidence)
# ----------------------------

@dataclass(frozen=True)
class DiffLine:
    path: str
    kind: Literal["add", "del", "ctx"]
    old_lineno: Optional[int]
    new_lineno: Optional[int]
    text: str  # line without leading "+", "-", " "


_FILE_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.MULTILINE)
_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", re.MULTILINE)

def parse_unified_diff(patch: str) -> List[DiffLine]:
    if not patch:
        return []

    lines = patch.splitlines()
    out: List[DiffLine] = []

    cur_path: Optional[str] = None
    old_ln: Optional[int] = None
    new_ln: Optional[int] = None

    i = 0
    while i < len(lines):
        line = lines[i]

        mfile = _FILE_RE.match(line)
        if mfile:
            cur_path = mfile.group(2)  # prefer b/<path>
            old_ln = None
            new_ln = None
            i += 1
            continue

        mhunk = _HUNK_RE.match(line)
        if mhunk:
            old_ln = int(mhunk.group(1))
            new_ln = int(mhunk.group(3))
            i += 1
            continue

        if cur_path is None:
            i += 1
            continue

        if line.startswith("+") and not line.startswith("+++"):
            text = line[1:]
            out.append(DiffLine(cur_path, "add", old_ln, new_ln, text))
            if new_ln is not None:
                new_ln += 1
            i += 1
            continue

        if line.startswith("-") and not line.startswith("---"):
            text = line[1:]
            out.append(DiffLine(cur_path, "del", old_ln, new_ln, text))
            if old_ln is not None:
                old_ln += 1
            i += 1
            continue

        if line.startswith(" "):
            text = line[1:]
            out.append(DiffLine(cur_path, "ctx", old_ln, new_ln, text))
            if old_ln is not None:
                old_ln += 1
            if new_ln is not None:
                new_ln += 1
            i += 1
            continue

        i += 1

    return out


# ----------------------------
# Strict strong extraction (ONLY definitions/assignments in +/- lines)
# ----------------------------

_DEF_FUNC_RE = re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\(")
_DEF_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\s*[:\(]")
_ASSIGN_CONST_RE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*=")
_ASSIGN_SELF_ATTR_RE = re.compile(r"^\s*self\.([A-Za-z_]\w*)\s*=")

@dataclass
class PatchSymbolsStrict:
    defined_functions: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    defined_classes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    assigned_consts: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    assigned_self_attrs: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def all_symbols(self) -> Set[str]:
        return set(self.defined_functions) | set(self.defined_classes) | set(self.assigned_consts) | set(self.assigned_self_attrs)

def _push(bucket: Dict[str, List[Dict[str, Any]]], sym: str, ev: Dict[str, Any]) -> None:
    bucket.setdefault(sym, []).append(ev)

def extract_strong_symbols_with_evidence(patch: str) -> PatchSymbolsStrict:
    parsed = parse_unified_diff(patch)
    out = PatchSymbolsStrict()

    for dl in parsed:
        if dl.kind not in ("add", "del"):
            continue  # STRICT: strong only from +/- lines

        # function def
        m = _DEF_FUNC_RE.match(dl.text)
        if m:
            sym = m.group(1)
            ev = {
                "type": "diff_definition",
                "symbol": sym,
                "path": dl.path,
                "line": dl.new_lineno if dl.kind == "add" else dl.old_lineno,
                "snippet": dl.text.strip()[:300],
            }
            _push(out.defined_functions, sym, ev)
            continue

        # class def
        m = _DEF_CLASS_RE.match(dl.text)
        if m:
            sym = m.group(1)
            ev = {
                "type": "diff_definition",
                "symbol": sym,
                "path": dl.path,
                "line": dl.new_lineno if dl.kind == "add" else dl.old_lineno,
                "snippet": dl.text.strip()[:300],
            }
            _push(out.defined_classes, sym, ev)
            continue

        # CONST assignment
        m = _ASSIGN_CONST_RE.match(dl.text)
        if m:
            sym = m.group(1)
            ev = {
                "type": "diff_assignment",
                "symbol": sym,
                "path": dl.path,
                "line": dl.new_lineno if dl.kind == "add" else dl.old_lineno,
                "snippet": dl.text.strip()[:300],
            }
            _push(out.assigned_consts, sym, ev)
            continue

        # self.attr assignment
        m = _ASSIGN_SELF_ATTR_RE.match(dl.text)
        if m:
            sym = f"self.{m.group(1)}"
            ev = {
                "type": "diff_assignment",
                "symbol": sym,
                "path": dl.path,
                "line": dl.new_lineno if dl.kind == "add" else dl.old_lineno,
                "snippet": dl.text.strip()[:300],
            }
            _push(out.assigned_self_attrs, sym, ev)
            continue

    return out


# ----------------------------
# Grounding result
# ----------------------------

@dataclass
class GroundingResult:
    status: GroundingStatus
    level: int  # 0 none, 1 strong, 2 weak_file, 3 weak_ref
    matched_symbols: Set[str] = field(default_factory=set)
    unmatched_symbols: Set[str] = field(default_factory=set)
    rule: str = ""
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "level": self.level,
            "matched_symbols": sorted(self.matched_symbols),
            "unmatched_symbols": sorted(self.unmatched_symbols),
            "rule": self.rule,
            "evidence": self.evidence,
        }

def _status_to_level(status: GroundingStatus) -> int:
    return {"none": 0, "strong": 1, "weak_file": 2, "weak_ref": 3}[status]


def calculate_grounding_strength(
    claim: Dict[str, Any],
    patch: str,
    *,
    touched_files_text: Optional[Dict[str, str]] = None,
    code_context: Optional[str] = None,
) -> GroundingResult:
    """
    v2.1 grounding:

    STRONG:
      - only if target symbol matches something DEFINED/ASSIGNED in diff (+/- lines)
      - evidence comes from diff_definition/diff_assignment entries

    WEAK_FILE:
      - symbol appears in full touched file text (requires touched_files_text)

    WEAK_REF:
      - symbol appears in code_context (imports/references) (best effort)

    NONE:
      - no match
    """
    targets = [s for s in (claim.get("target_symbols") or []) if isinstance(s, str) and s.strip()]
    target_set = set(targets)

    if not target_set:
        return GroundingResult(status="none", level=0, rule="no_target_symbols")

    strong = extract_strong_symbols_with_evidence(patch)
    strong_syms = strong.all_symbols()

    normalized_strong: Set[str] = set()
    for s in strong_syms:
        normalized_strong |= normalize_symbol(s)

    matched: Set[str] = set()
    unmatched: Set[str] = set(target_set)
    evidence: List[Dict[str, Any]] = []

    # STRONG match
    for t in target_set:
        t_norm = normalize_symbol(t)

        # prevent accidental matching on pure builtins targets unless explicitly in diff (rare)
        if t in _BUILTIN_NOISE and "." not in t:
            # still allow if it's actually defined in diff
            pass

        if t_norm & normalized_strong:
            matched.add(t)
            unmatched.discard(t)

            for s in strong_syms:
                if normalize_symbol(s) & t_norm:
                    evidence.extend(strong.defined_functions.get(s, []))
                    evidence.extend(strong.defined_classes.get(s, []))
                    evidence.extend(strong.assigned_consts.get(s, []))
                    evidence.extend(strong.assigned_self_attrs.get(s, []))

    if matched:
        return GroundingResult(
            status="strong",
            level=_status_to_level("strong"),
            matched_symbols=matched,
            unmatched_symbols=unmatched,
            rule="symbol_in_diff_definition_or_assignment",
            evidence=evidence[:50],
        )

    # WEAK_FILE (requires touched file texts)
    if touched_files_text:
        touched_paths = set(m.group(2) for m in _FILE_RE.finditer(patch))
        for t in target_set:
            t_norm = normalize_symbol(t)
            found = False
            for p in touched_paths:
                txt = touched_files_text.get(p)
                if not txt:
                    continue
                # simple containment check
                if any(v in txt for v in t_norm):
                    found = True
                    evidence.append({
                        "type": "file_reference",
                        "symbol": t,
                        "path": p,
                        "line": None,
                        "snippet": f"...{t}...",
                    })
                    break
            if found:
                matched.add(t)
                unmatched.discard(t)

        if matched:
            return GroundingResult(
                status="weak_file",
                level=_status_to_level("weak_file"),
                matched_symbols=matched,
                unmatched_symbols=unmatched,
                rule="symbol_in_touched_file_not_in_diff_definition",
                evidence=evidence[:50],
            )

    # WEAK_REF (best effort)
    if code_context:
        ctx = code_context
        for t in target_set:
            t_norm = normalize_symbol(t)
            if any(v in ctx for v in t_norm if len(v) >= 2):
                matched.add(t)
                unmatched.discard(t)
                evidence.append({
                    "type": "import_reference",
                    "symbol": t,
                    "path": "code_context",
                    "line": None,
                    "snippet": f"...{t}...",
                })

        if matched:
            return GroundingResult(
                status="weak_ref",
                level=_status_to_level("weak_ref"),
                matched_symbols=matched,
                unmatched_symbols=unmatched,
                rule="symbol_in_code_context_reference",
                evidence=evidence[:50],
            )

    return GroundingResult(
        status="none",
        level=_status_to_level("none"),
        matched_symbols=set(),
        unmatched_symbols=unmatched,
        rule="no_match",
        evidence=[],
    )


def is_claim_grounded(
    claim: Dict[str, Any],
    patch: str,
    *,
    min_status: GroundingStatus = "weak_ref",
    touched_files_text: Optional[Dict[str, str]] = None,
    code_context: Optional[str] = None,
) -> bool:
    """
    Ordering: strong > weak_file > weak_ref > none
    """
    res = calculate_grounding_strength(claim, patch, touched_files_text=touched_files_text, code_context=code_context)
    order = {"none": 0, "weak_ref": 1, "weak_file": 2, "strong": 3}
    return order[res.status] >= order[min_status]


def filter_grounded_claims(
    claims: List[Dict[str, Any]],
    patch: str,
    *,
    min_status: GroundingStatus = "weak_ref",
    touched_files_text: Optional[Dict[str, str]] = None,
    code_context: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    grounded: List[Dict[str, Any]] = []
    ungrounded: List[Dict[str, Any]] = []

    for c in claims:
        res = calculate_grounding_strength(c, patch, touched_files_text=touched_files_text, code_context=code_context)
        if is_claim_grounded(c, patch, min_status=min_status, touched_files_text=touched_files_text, code_context=code_context):
            cc = dict(c)
            cc["grounding"] = res.to_dict()
            grounded.append(cc)
        else:
            ungrounded.append(c)

    return grounded, ungrounded


def extract_symbols_from_diff_strict(patch: str) -> Set[str]:
    """
    Backwards helper: returns ONLY strong symbols (definitions/assignments).
    """
    return extract_strong_symbols_with_evidence(patch).all_symbols()
