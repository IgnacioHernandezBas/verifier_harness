"""Extract and sanitize code examples from repository test files."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


def extract_fixture_usage_examples(
    repo_path: Path,
    test_files: List[str],
    fixture_name: str,
    claim_keywords: List[str],
) -> Optional[str]:
    """
    Extract generic fixture usage examples from test files.

    Finds real examples of how to use pytest fixtures in this repo,
    while filtering out claim-specific tests to avoid leakage.

    Args:
        repo_path: Path to the repository
        test_files: List of test file paths from commit_diff
        fixture_name: The fixture to find examples for (e.g., "tmpdir_factory")
        claim_keywords: Keywords from claim to avoid leaking similar tests

    Returns:
        Sanitized example string or None if no suitable examples found
    """
    for test_file in test_files:
        full_path = repo_path / test_file
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        # Find test functions that use this fixture
        pattern = rf'def\s+(test_\w+)\s*\([^)]*\b{re.escape(fixture_name)}\b[^)]*\):'
        matches = list(re.finditer(pattern, content))

        for match in matches:
            # Extract the function and a few lines
            func_name = match.group(1)
            start_pos = match.start()

            # Find the end of this function (next def or end of file)
            next_def = content.find('\ndef ', start_pos + 1)
            next_class = content.find('\nclass ', start_pos + 1)

            end_pos = len(content)
            if next_def != -1:
                end_pos = min(end_pos, next_def)
            if next_class != -1:
                end_pos = min(end_pos, next_class)

            # Extract function body (limit to first ~200 chars for safety)
            func_body = content[start_pos:min(start_pos + 300, end_pos)]

            # Check if example is too similar to claim
            if _is_example_too_similar(func_body, claim_keywords):
                continue

            # Sanitize the example
            sanitized = _sanitize_example(func_body, max_lines=5, claim_keywords=claim_keywords)

            if sanitized and len(sanitized.strip()) > 20:  # Ensure we got something useful
                return (
                    f"**Example from {test_file}:**\n"
                    f"```python\n{sanitized}\n```"
                )

    return None


def extract_import_patterns(
    repo_path: Path,
    test_files: List[str],
    module_path: str,
) -> Optional[str]:
    """
    Extract import patterns from test files.

    Shows how the repo's own tests import from the target module,
    filtering out internal/private imports.

    Args:
        repo_path: Path to the repository
        test_files: List of test file paths
        module_path: Module to find imports for (e.g., "src._pytest.tmpdir")

    Returns:
        Example import statements or None
    """
    # Extract the base module name (e.g., "tmpdir" from "src._pytest.tmpdir")
    module_parts = module_path.split('.')
    if not module_parts:
        return None

    # Look for imports of this module
    import_patterns = []

    for test_file in test_files:
        full_path = repo_path / test_file
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        # Find import statements (but skip internal ones)
        for line in content.split('\n')[:50]:  # Only check first 50 lines
            line = line.strip()

            # Skip internal imports
            if '_pytest' in line or '._internal' in line or '._private' in line:
                continue

            # Look for relevant imports
            if 'import' in line and any(part in line for part in module_parts):
                import_patterns.append(line)
                if len(import_patterns) >= 3:  # Limit to 3 examples
                    break

        if import_patterns:
            break

    if import_patterns:
        examples = '\n'.join(import_patterns)
        return f"**Import examples from {test_files[0] if test_files else 'tests'}:**\n```python\n{examples}\n```"

    return None


def extract_claim_keywords(claim_text: str, given: str, when: str) -> List[str]:
    """
    Extract keywords from claim to detect similar tests.

    Purpose: Identify claim-specific words to filter examples and
    prevent leaking tests that solve the same problem.

    Args:
        claim_text: Main claim text
        given: Given clause
        when: When clause

    Returns:
        List of lowercase keywords

    Examples:
        "illegal characters" → ["illegal", "character"]
        "FileNotFoundError" → ["filenotfound", "notfound"]
    """
    combined = f"{claim_text} {given} {when}".lower()

    # Extract meaningful words (skip common words)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'that',
        'this', 'these', 'those', 'when', 'where', 'why', 'how', 'which',
        'who', 'what', 'if', 'then', 'else', 'when', 'not', 'no', 'yes',
    }

    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[a-z][a-z0-9]*\b', combined)

    # Filter and deduplicate
    keywords = []
    seen = set()

    for word in words:
        if len(word) < 3:  # Skip very short words
            continue
        if word in stop_words:
            continue
        if word not in seen:
            keywords.append(word)
            seen.add(word)

    # Also extract camelCase/exception names
    exception_pattern = r'\b([A-Z][a-z]+(?:Error|Exception|Warning))\b'
    exceptions = re.findall(exception_pattern, claim_text + given + when)
    for exc in exceptions:
        keywords.append(exc.lower())

    return keywords


def _sanitize_example(
    code: str,
    max_lines: int = 4,
    claim_keywords: List[str] = None,
) -> str:
    """
    Remove test logic, keep only API usage patterns.

    Removes:
    - Lines with: assert, expect, should, ==, !=
    - Lines containing claim keywords
    - Everything after first assertion

    Keeps:
    - Function signature
    - Fixture parameters
    - Basic API calls (first few lines)

    Args:
        code: Code to sanitize
        max_lines: Maximum lines to include
        claim_keywords: Keywords to filter out

    Returns:
        Sanitized code
    """
    if claim_keywords is None:
        claim_keywords = []

    lines = code.split('\n')
    sanitized = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()

        # Always keep function signature
        if stripped.startswith('def ') and i == 0:
            sanitized.append(line)
            continue

        # Stop at first assertion
        if any(pattern in lower for pattern in ['assert', '== ', '!= ', 'expect', 'should']):
            break

        # Skip lines with claim keywords
        if any(keyword in lower for keyword in claim_keywords if keyword):
            continue

        # Skip comment-only lines or empty lines (except first line after def)
        if not stripped or stripped.startswith('#'):
            continue

        # Skip docstrings
        if '"""' in stripped or "'''" in stripped:
            continue

        # Add the line
        sanitized.append(line)

        # Limit total lines
        if len(sanitized) >= max_lines:
            break

    return '\n'.join(sanitized)


def _is_example_too_similar(
    example_code: str,
    claim_keywords: List[str],
    similarity_threshold: float = 0.3,
) -> bool:
    """
    Check if example is too similar to the claim.

    Purpose: Prevent leaking the gold test by filtering examples
    that solve the exact same problem.

    Args:
        example_code: Code to check
        claim_keywords: Keywords from the claim
        similarity_threshold: Fraction of keywords that trigger filtering

    Returns:
        True if example is too similar and should be skipped

    Logic:
        - Count keyword matches in example
        - If >30% of keywords match, consider it too similar
    """
    if not claim_keywords:
        return False

    example_lower = example_code.lower()

    # Count how many claim keywords appear in the example
    matches = sum(1 for keyword in claim_keywords if keyword in example_lower)

    # Calculate similarity ratio
    similarity = matches / len(claim_keywords) if claim_keywords else 0

    return similarity > similarity_threshold
