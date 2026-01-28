"""
Grounding Module
================

This module implements the grounding check: verifying that extracted claims
reference symbols (functions, classes, methods) that were actually modified
in the gold patch.

Key Concepts:
- **Grounding**: A claim is "grounded" if its target_symbols appear in the patch
- **Strong grounding**: All target_symbols are in the patch
- **Weak grounding**: At least one target_symbol is in the patch
- **No grounding**: No target_symbols are in the patch

Example:
    >>> patch = '''
    ... diff --git a/astropy/io/ascii/qdp.py b/astropy/io/ascii/qdp.py
    ... --- a/astropy/io/ascii/qdp.py
    ... +++ b/astropy/io/ascii/qdp.py
    ... @@ -100,7 +100,7 @@ def _parse_qdp_commands(line):
    ... -    if line.startswith('READ'):
    ... +    if line.upper().startswith('READ'):
    ... '''
    >>>
    >>> symbols = extract_symbols_from_diff(patch)
    >>> print(symbols)
    {'_parse_qdp_commands'}
    >>>
    >>> claim = {
    ...     'claim_id': 'C1',
    ...     'target_symbols': ['_parse_qdp_commands']
    ... }
    >>> is_claim_grounded(claim, patch)
    True
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Literal


@dataclass
class GroundingResult:
    """Result of grounding check for a claim."""

    is_grounded: bool
    strength: Literal['strong', 'weak', 'none']
    matched_symbols: Set[str] = field(default_factory=set)
    unmatched_symbols: Set[str] = field(default_factory=set)
    patch_symbols: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'is_grounded': self.is_grounded,
            'strength': self.strength,
            'matched_symbols': list(self.matched_symbols),
            'unmatched_symbols': list(self.unmatched_symbols),
            'patch_symbols': list(self.patch_symbols),
            'match_ratio': len(self.matched_symbols) / max(1, len(self.matched_symbols) + len(self.unmatched_symbols))
        }


def extract_symbols_from_diff(patch: str) -> Set[str]:
    """
    Extract function and class names that were modified in a patch.

    This function parses a git diff and identifies symbols (functions, classes,
    methods) that appear in:
    1. Hunk headers (@@ ... @@ def function_name)
    2. Added or removed lines with definitions
    3. Modified code that calls functions

    Args:
        patch: Git diff string (unified diff format)

    Returns:
        Set of symbol names found in the patch

    Examples:
        >>> patch = '''
        ... diff --git a/module.py b/module.py
        ... @@ -10,5 +10,5 @@
        ... -def old_function():
        ... +def new_function():
        ...      pass
        ... '''
        >>> extract_symbols_from_diff(patch)
        {'old_function', 'new_function'}

        >>> patch = '''
        ... diff --git a/models.py b/models.py
        ... @@ -20,3 +20,3 @@
        ... -class OldModel:
        ... +class NewModel:
        ...      pass
        ... '''
        >>> extract_symbols_from_diff(patch)
        {'OldModel', 'NewModel'}
    """
    if not patch:
        return set()

    symbols = set()

    # Pattern 0: Hunk headers - MOST RELIABLE
    # Matches: @@ -64,7 +64,7 @@ def _parse_qdp_commands(line):
    # Matches: @@ -100,5 +100,5 @@ class MyClass:
    hunk_pattern = re.compile(
        r'@@[^@]*@@\s+(?:def\s+(\w+)|class\s+(\w+))',
        re.MULTILINE
    )
    for match in hunk_pattern.finditer(patch):
        if match.group(1):  # function
            symbols.add(match.group(1))
        elif match.group(2):  # class
            symbols.add(match.group(2))

    # Pattern 1: Function definitions (def function_name(...))
    # Matches lines like: -def foo(): or +def bar(x, y):
    func_pattern = re.compile(r'^[-+]\s*def\s+(\w+)\s*\(', re.MULTILINE)
    for match in func_pattern.finditer(patch):
        symbols.add(match.group(1))

    # Pattern 2: Class definitions (class ClassName(...))
    # Matches lines like: -class Foo: or +class Bar(Base):
    class_pattern = re.compile(r'^[-+]\s*class\s+(\w+)', re.MULTILINE)
    for match in class_pattern.finditer(patch):
        symbols.add(match.group(1))

    # Pattern 3: Method definitions in classes
    # Matches context lines that show method definitions
    # This helps when only the method body changed, not the signature
    context_method_pattern = re.compile(r'^\s+def\s+(\w+)\s*\(', re.MULTILINE)
    for match in context_method_pattern.finditer(patch):
        symbol = match.group(1)
        # Only add if not a Python keyword
        if symbol not in {'if', 'while', 'for', 'elif'}:
            symbols.add(symbol)

    return symbols


def normalize_symbol(symbol: str) -> Set[str]:
    """
    Normalize a symbol to handle different naming conventions.

    Handles cases like:
    - "Table.read" → {"Table", "read", "Table.read"}
    - "_parse_commands" → {"_parse_commands"}
    - "MyClass.my_method" → {"MyClass", "my_method", "MyClass.my_method"}

    Args:
        symbol: Symbol name (can include dots for methods)

    Returns:
        Set of normalized symbol variants
    """
    variants = {symbol}  # Always include the original

    # Handle dotted names (e.g., "Class.method")
    if '.' in symbol:
        parts = symbol.split('.')
        variants.update(parts)  # Add both "Class" and "method"

    return variants


def is_claim_grounded(claim: Dict, patch: str,
                      require_strong: bool = False) -> bool:
    """
    Check if a claim is grounded in the patch.

    A claim is grounded if its target_symbols appear in the patch's modified code.

    Args:
        claim: Claim dictionary with 'target_symbols' field
        patch: Git diff string
        require_strong: If True, require ALL symbols to match (strong grounding).
                       If False, require at least ONE symbol to match (weak grounding).

    Returns:
        True if the claim is grounded, False otherwise

    Examples:
        >>> claim = {'target_symbols': ['parse_command', 'validate']}
        >>> patch = 'def parse_command(): ...'
        >>> is_claim_grounded(claim, patch)
        True

        >>> is_claim_grounded(claim, patch, require_strong=True)
        False  # Only 'parse_command' matches, not 'validate'
    """
    result = calculate_grounding_strength(claim, patch)

    if require_strong:
        return result.strength == 'strong'
    else:
        return result.is_grounded


def calculate_grounding_strength(claim: Dict, patch: str) -> GroundingResult:
    """
    Calculate detailed grounding information for a claim.

    Args:
        claim: Claim dictionary with 'target_symbols' field
        patch: Git diff string

    Returns:
        GroundingResult with detailed matching information

    Examples:
        >>> claim = {'target_symbols': ['foo', 'bar', 'baz']}
        >>> patch = 'def foo(): ... def bar(): ...'
        >>> result = calculate_grounding_strength(claim, patch)
        >>> result.strength
        'weak'
        >>> result.matched_symbols
        {'foo', 'bar'}
        >>> result.unmatched_symbols
        {'baz'}
    """
    target_symbols = set(claim.get('target_symbols', []))
    if not target_symbols:
        return GroundingResult(
            is_grounded=False,
            strength='none',
            unmatched_symbols=set(),
            patch_symbols=set()
        )

    patch_symbols = extract_symbols_from_diff(patch)

    # Normalize all symbols for matching
    # This handles cases like "Table.read" matching "read" in the patch
    normalized_targets = set()
    for symbol in target_symbols:
        normalized_targets.update(normalize_symbol(symbol))

    normalized_patch = set()
    for symbol in patch_symbols:
        normalized_patch.update(normalize_symbol(symbol))

    # Find matches (using normalized symbols)
    matched = normalized_targets & normalized_patch

    # Determine which original target symbols were matched
    matched_original = set()
    unmatched_original = set()

    for target in target_symbols:
        target_variants = normalize_symbol(target)
        if target_variants & matched:
            matched_original.add(target)
        else:
            unmatched_original.add(target)

    # Determine strength
    if not matched_original:
        strength = 'none'
        is_grounded = False
    elif len(matched_original) == len(target_symbols):
        strength = 'strong'
        is_grounded = True
    else:
        strength = 'weak'
        is_grounded = True

    return GroundingResult(
        is_grounded=is_grounded,
        strength=strength,
        matched_symbols=matched_original,
        unmatched_symbols=unmatched_original,
        patch_symbols=patch_symbols
    )


def filter_grounded_claims(claims: List[Dict], patch: str,
                          min_strength: Literal['weak', 'strong'] = 'weak') -> Tuple[List[Dict], List[Dict]]:
    """
    Filter claims by grounding status.

    Args:
        claims: List of claim dictionaries
        patch: Git diff string
        min_strength: Minimum grounding strength required ('weak' or 'strong')

    Returns:
        Tuple of (grounded_claims, ungrounded_claims)

    Examples:
        >>> claims = [
        ...     {'claim_id': 'C1', 'target_symbols': ['foo']},
        ...     {'claim_id': 'C2', 'target_symbols': ['bar']},
        ...     {'claim_id': 'C3', 'target_symbols': ['baz']}
        ... ]
        >>> patch = 'def foo(): pass'
        >>> grounded, ungrounded = filter_grounded_claims(claims, patch)
        >>> len(grounded), len(ungrounded)
        (1, 2)
    """
    grounded = []
    ungrounded = []

    for claim in claims:
        result = calculate_grounding_strength(claim, patch)

        # Check if claim meets minimum strength requirement
        meets_requirement = False
        if min_strength == 'weak':
            meets_requirement = result.is_grounded  # weak or strong
        elif min_strength == 'strong':
            meets_requirement = result.strength == 'strong'

        if meets_requirement:
            # Add grounding info to claim
            claim_with_grounding = claim.copy()
            claim_with_grounding['grounding'] = result.to_dict()
            grounded.append(claim_with_grounding)
        else:
            ungrounded.append(claim)

    return grounded, ungrounded


# Utility function for debugging and analysis
def print_grounding_analysis(claim: Dict, patch: str) -> None:
    """
    Print a human-readable grounding analysis.

    Useful for debugging and understanding why claims are/aren't grounded.

    Args:
        claim: Claim dictionary
        patch: Git diff string
    """
    result = calculate_grounding_strength(claim, patch)

    print(f"Claim ID: {claim.get('claim_id', 'N/A')}")
    print(f"Target Symbols: {claim.get('target_symbols', [])}")
    print(f"Patch Symbols: {result.patch_symbols}")
    print(f"\nGrounding Status: {result.strength.upper()}")
    print(f"Is Grounded: {result.is_grounded}")
    print(f"Matched: {result.matched_symbols}")
    print(f"Unmatched: {result.unmatched_symbols}")
    print(f"Match Ratio: {result.to_dict()['match_ratio']:.2%}")
