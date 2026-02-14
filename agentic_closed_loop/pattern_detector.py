"""Detect anti-patterns in generated test code."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def detect_fixture_misuse(code: str) -> Optional[Dict[str, str]]:
    """
    Detect when agent tries to access fixtures as module attributes.

    Identifies patterns like:
    - pytest.tmpdir_factory
    - pytest.tmpdir
    - pytest.monkeypatch (wrong usage)

    But allows valid usage like:
    - pytest.raises
    - pytest.mark
    - pytest.skip

    Args:
        code: Generated test code

    Returns:
        Dictionary with pattern info or None if no misuse detected:
        {
            "pattern": "fixture_attribute_error",
            "fixture_name": "tmpdir_factory",
            "line": "pytest.tmpdir_factory.mktemp('foo')"
        }
    """
    # Known valid pytest module attributes (not fixtures)
    valid_attributes = {
        'raises', 'mark', 'skip', 'skipif', 'xfail', 'param', 'fixture',
        'fail', 'warns', 'deprecated_call', 'register_assert_rewrite',
        'exit', 'importorskip', 'main', 'yield_fixture', 'approx',
    }

    # Known fixtures that are commonly misused
    fixture_names = {
        'tmpdir', 'tmpdir_factory', 'tmp_path', 'tmp_path_factory',
        'monkeypatch', 'capsys', 'capfd', 'capfdbinary', 'capsysbinary',
        'request', 'cache', 'pytestconfig', 'record_property',
        'record_testsuite_property', 'recwarn', 'doctest_namespace',
    }

    # Pattern: pytest.something (but not valid attributes)
    pattern = r'pytest\.([a-z_][a-z0-9_]*)'

    for match in re.finditer(pattern, code):
        attr_name = match.group(1)

        # Skip if it's a valid module attribute
        if attr_name in valid_attributes:
            continue

        # Check if it's a known fixture
        if attr_name in fixture_names:
            # Extract the line for context
            line_start = code.rfind('\n', 0, match.start()) + 1
            line_end = code.find('\n', match.end())
            if line_end == -1:
                line_end = len(code)
            line = code[line_start:line_end].strip()

            return {
                "pattern": "fixture_attribute_error",
                "fixture_name": attr_name,
                "line": line,
            }

    return None


def detect_internal_import_attempt(code: str) -> Optional[Dict[str, str]]:
    """
    Detect imports from internal/private modules.

    Identifies patterns like:
    - from _pytest.tmpdir import TempdirFactory
    - from package._internal import helper
    - from src._pytest.something import Class

    Args:
        code: Generated test code

    Returns:
        Dictionary with pattern info or None:
        {
            "pattern": "internal_import",
            "module": "_pytest.tmpdir",
            "imported_name": "TempdirFactory"
        }
    """
    # Pattern for: from _something or from package._something
    from_pattern = r'from\s+((?:\w+\.)*_\w+(?:\.\w+)*)\s+import\s+(\w+(?:\s*,\s*\w+)*)'

    match = re.search(from_pattern, code)
    if match:
        module = match.group(1)
        imported_names = match.group(2)

        # Clean up imported names
        names = [n.strip() for n in imported_names.split(',')]

        return {
            "pattern": "internal_import",
            "module": module,
            "imported_name": names[0] if names else "unknown",
            "all_imports": names,
        }

    # Also check for: import _something
    import_pattern = r'import\s+(_\w+(?:\.\w+)*)'
    match = re.search(import_pattern, code)
    if match:
        module = match.group(1)
        return {
            "pattern": "internal_import",
            "module": module,
            "imported_name": module.split('.')[-1],
        }

    return None


def detect_nonexistent_pytest_api(code: str) -> Optional[Dict[str, str]]:
    """
    Detect usage of non-existent pytest APIs.

    Common mistakes:
    - pytest.MonkeyPatch.context()
    - pytest.tmpdir.mkdir()
    - Creating classes that should be fixtures

    Args:
        code: Generated test code

    Returns:
        Dictionary with pattern info or None
    """
    # Pattern: pytest.CapitalizedClass (usually wrong)
    pattern = r'pytest\.([A-Z][a-zA-Z0-9]*)'

    for match in re.finditer(pattern, code):
        class_name = match.group(1)

        # Extract the line for context
        line_start = code.rfind('\n', 0, match.start()) + 1
        line_end = code.find('\n', match.end())
        if line_end == -1:
            line_end = len(code)
        line = code[line_start:line_end].strip()

        return {
            "pattern": "nonexistent_pytest_api",
            "api_name": class_name,
            "line": line,
        }

    return None


def detect_incorrect_fixture_creation(code: str) -> Optional[Dict[str, str]]:
    """
    Detect attempts to manually create fixtures.

    Patterns like:
    - TempdirFactory(basetemp=...)
    - TempPathFactory(...)
    - MonkeyPatch()

    Args:
        code: Generated test code

    Returns:
        Dictionary with pattern info or None
    """
    # Known fixture classes that shouldn't be instantiated
    fixture_classes = {
        'TempdirFactory', 'TempPathFactory', 'MonkeyPatch',
        'CaptureFixture', 'LogCaptureFixture',
    }

    for class_name in fixture_classes:
        # Pattern: ClassName(...) - instantiation
        pattern = rf'\b{class_name}\s*\('

        match = re.search(pattern, code)
        if match:
            # Extract the line for context
            line_start = code.rfind('\n', 0, match.start()) + 1
            line_end = code.find('\n', match.end())
            if line_end == -1:
                line_end = len(code)
            line = code[line_start:line_end].strip()

            return {
                "pattern": "incorrect_fixture_creation",
                "class_name": class_name,
                "line": line,
            }

    return None


def detect_common_antipatterns(code: str, error: str = "") -> List[Dict[str, Any]]:
    """
    Run all pattern detectors and return findings.

    This is the main entry point for pattern detection.

    Args:
        code: Generated test code
        error: Error message from test execution (optional)

    Returns:
        List of detected anti-patterns, each as a dictionary
    """
    patterns = []

    # Detect fixture misuse (pytest.tmpdir_factory, etc.)
    fixture_misuse = detect_fixture_misuse(code)
    if fixture_misuse:
        patterns.append(fixture_misuse)

    # Detect internal imports
    internal_import = detect_internal_import_attempt(code)
    if internal_import:
        patterns.append(internal_import)

    # Detect non-existent pytest APIs
    nonexistent_api = detect_nonexistent_pytest_api(code)
    if nonexistent_api:
        patterns.append(nonexistent_api)

    # Detect incorrect fixture creation
    incorrect_creation = detect_incorrect_fixture_creation(code)
    if incorrect_creation:
        patterns.append(incorrect_creation)

    return patterns
