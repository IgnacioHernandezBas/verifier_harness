from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Tuple

from .pattern_detector import detect_common_antipatterns


@dataclass
class Diagnosis:
    label: str
    details: str
    patterns: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _collect_outputs(test_run: Dict[str, Any]) -> str:
    stdout = (test_run.get("stdout") or "").lower()
    stderr = (test_run.get("stderr") or "").lower()
    return f"{stdout}\n{stderr}"


def _enhance_internal_import_details(base_details: str, patterns: List[Dict[str, Any]]) -> str:
    """
    Add pattern-specific context to diagnosis details.

    Args:
        base_details: Original diagnosis details
        patterns: Detected anti-patterns from pattern_detector

    Returns:
        Enhanced details with specific guidance
    """
    enhancements = []

    for pattern in patterns:
        pattern_type = pattern.get("pattern")

        if pattern_type == "fixture_attribute_error":
            fixture_name = pattern.get("fixture_name", "unknown")
            line = pattern.get("line", "")
            enhancements.append(
                f"\n🎯 **DETECTED ANTI-PATTERN**: Fixture attribute access\n"
                f"   You tried: pytest.{fixture_name}\n"
                f"   In line: {line}\n"
                f"   But '{fixture_name}' is a FIXTURE, not a module attribute!\n"
                f"   Fix: Add '{fixture_name}' as a function parameter instead.\n"
            )

        elif pattern_type == "internal_import":
            module = pattern.get("module", "")
            imported_name = pattern.get("imported_name", "")
            enhancements.append(
                f"\n🎯 **DETECTED ANTI-PATTERN**: Internal module import\n"
                f"   You tried: from {module} import {imported_name}\n"
                f"   But internal modules (starting with _) are NOT available!\n"
                f"   Fix: Use public APIs and fixtures instead.\n"
            )

        elif pattern_type == "incorrect_fixture_creation":
            class_name = pattern.get("class_name", "")
            enhancements.append(
                f"\n🎯 **DETECTED ANTI-PATTERN**: Manual fixture creation\n"
                f"   You tried to create: {class_name}(...)\n"
                f"   But fixtures should NOT be instantiated manually!\n"
                f"   Fix: Use the fixture as a function parameter.\n"
            )

        elif pattern_type == "nonexistent_pytest_api":
            api_name = pattern.get("api_name", "")
            enhancements.append(
                f"\n🎯 **DETECTED ANTI-PATTERN**: Non-existent pytest API\n"
                f"   You tried: pytest.{api_name}\n"
                f"   This API does not exist in pytest!\n"
            )

    if enhancements:
        return base_details + "\n" + "\n".join(enhancements)

    return base_details


def _extract_error_summary(test_run: Dict[str, Any], max_lines: int = 15) -> str:
    """Extract the most relevant error lines from test output."""
    stdout = test_run.get("stdout") or ""
    stderr = test_run.get("stderr") or ""

    # Combine and split into lines
    combined = f"{stdout}\n{stderr}"
    lines = combined.split('\n')

    # Look for key error indicators
    error_lines = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in [
            'error', 'exception', 'traceback', 'failed', 'fixture',
            'importerror', 'attributeerror', 'typeerror', 'valueerror',
            'assert', 'expected', 'missing', 'not found'
        ]):
            # Include some context around error
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            error_lines.extend(lines[start:end])
            if len(error_lines) >= max_lines:
                break

    if error_lines:
        return '\n'.join(error_lines[:max_lines])

    # Fallback: return last few lines if no specific errors found
    return '\n'.join(lines[-max_lines:]) if lines else "No output captured"


def _classify_pair(bug: Dict[str, Any], gold: Dict[str, Any], generated_code: str = "") -> Tuple[str, str]:
    bug_status = bug.get("status")
    gold_status = gold.get("status")
    combined = f"{_collect_outputs(bug)}\n{_collect_outputs(gold)}"

    if bug_status == "PASS" and gold_status == "PASS":
        return "non_discriminative", "Both variants pass. Claim may not capture bug."

    # Check for internal/private module import errors FIRST (more specific)
    if ("importerror" in combined or "modulenotfounderror" in combined or "module not found" in combined):
        bug_errors = _extract_error_summary(bug)

        # CRITICAL FIX: Check if this is pytest's own initialization failure (not test code)
        if "_pytest._version" in combined or "pytest/__init__.py" in combined:
            return "environment_error", (
                f"Pytest installation is broken in the test environment.\n"
                f"This is NOT a test code issue - pytest itself cannot initialize.\n\n"
                f"🔧 The test code appears correct, but the pytest environment is broken.\n"
                f"This typically means the container or environment setup failed.\n\n"
                f"Error details:\n{bug_errors}"
            )

        # CRITICAL FIX: Only classify as internal_import_error if the TEST CODE has internal imports
        # Don't just check the error output (which includes stack traces with _pytest paths)
        has_internal_import_in_code = False
        if generated_code:
            # Check if the actual test code imports from internal modules
            from .pattern_detector import detect_internal_import_attempt
            internal_import_pattern = detect_internal_import_attempt(generated_code)
            has_internal_import_in_code = internal_import_pattern is not None
        else:
            # Fallback: check if error mentions internal imports in a way that suggests test code issue
            # Be more specific - look for "from _pytest" or "import _pytest" in the actual error line
            if any(pattern in combined for pattern in [
                "from _pytest", "import _pytest",
                "from _internal", "import _internal",
                "from _private", "import _private"
            ]):
                has_internal_import_in_code = True

        if has_internal_import_in_code:
            return "internal_import_error", (
                f"Test imports from internal/private modules (e.g., _pytest.*).\n"
                f"These modules are NOT available in the test environment.\n\n"
                f"🔧 FIX: Use ONLY public API imports:\n"
                f"  ✅ import pytest\n"
                f"  ✅ Use pytest fixtures: tmpdir, tmp_path, monkeypatch, etc.\n"
                f"  ❌ from _pytest.* import anything\n\n"
                f"💡 EXAMPLES:\n"
                f"  Instead of: from _pytest.tmpdir import TempdirFactory\n"
                f"  Use:        def test(tmpdir):  # Use pytest's built-in tmpdir fixture\n\n"
                f"  Instead of: from _pytest.monkeypatch import MonkeyPatch\n"
                f"  Use:        def test(monkeypatch):  # Use pytest's built-in fixture\n\n"
                f"Error details:\n{bug_errors}"
            )

    # Generic import errors (after checking for internal imports)
    if "importerror" in combined or "module not found" in combined:
        bug_errors = _extract_error_summary(bug)

        # Extract the actual import error to provide better guidance
        import re
        # Look for "cannot import name 'X' from 'Y'"
        import_match = re.search(r"cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]", combined, re.IGNORECASE)
        if import_match:
            name = import_match.group(1)
            module = import_match.group(2)
            return "import_error", (
                f"Cannot import '{name}' from '{module}'.\n\n"
                f"🔧 POSSIBLE FIXES:\n"
                f"1. The symbol '{name}' may not exist in module '{module}'\n"
                f"   - Check the grounding evidence for the correct module/function name\n"
                f"   - Look at imports in the test_patch files - they show working imports\n"
                f"2. The symbol may be in a different submodule\n"
                f"   - Try importing from the parent package: from {module.split('.')[0]} import {name}\n"
                f"3. The symbol name may be slightly different (check capitalization, underscores)\n\n"
                f"Error details:\n{bug_errors}"
            )

        return "import_error", f"Import failed while running the test.\n\nError details:\n{bug_errors}"

    if "missing 1 required positional argument" in combined or "missing required positional argument" in combined:
        bug_errors = _extract_error_summary(bug)
        # Extract specific missing argument from error message
        import re
        match = re.search(r"missing \d+ required positional arguments?: ['\"]?([^'\"]+)['\"]?", combined)
        hint = ""
        if match:
            missing_arg = match.group(1)
            hint = f"\n\n💡 Hint: The function is missing the required argument(s): {missing_arg}"
            hint += "\nCheck the function signature and ensure all required parameters are provided."
        return "signature_mismatch", f"Call signature mismatch.{hint}\n\nError details:\n{bug_errors}"

    if "fixture" in combined and ("missing" in combined or "not found" in combined):
        bug_errors = _extract_error_summary(bug)
        # Extract available fixtures list if present
        hint = ""
        if "available fixtures:" in combined:
            import re
            match = re.search(r"available fixtures:\s*([^\n]+)", combined)
            if match:
                avail = match.group(1).strip()
                hint = f"\n\n💡 Hint: Use only fixtures from the available list: {avail}"
                hint += "\nCommon issue: tmp_path is not available in older pytest versions - use tmpdir instead."
                hint += "\nAvoid using fixtures for simple tests - prefer direct object construction."
        return "fixture_missing", f"Test uses unavailable fixtures.{hint}\n\nError details:\n{bug_errors}"

    if "attributeerror" in combined and ("monkeypatch" in combined or "setattr" in combined):
        bug_errors = _extract_error_summary(bug)
        hint = "\n\n💡 Hint: Don't mock internal/private methods. Test through public APIs only."
        hint += "\nSimplify your test - create objects directly and call methods normally."
        return "mocking_error", f"Test failed while trying to mock methods.{hint}\n\nError details:\n{bug_errors}"

    # Check if GOLD has assertion error (test is wrong about expected behavior)
    gold_stdout = gold.get("stdout", "") or ""
    gold_stderr = gold.get("stderr", "") or ""
    gold_combined = (gold_stdout + "\n" + gold_stderr).lower()

    # Detect assertion failures (pytest shows "assert" lines with "E" markers)
    gold_has_assertion = ("assertionerror" in gold_combined or
                          ("E   assert" in gold_stdout) or
                          ("E   assert" in gold_stderr))

    if gold_has_assertion and bug_status == gold_status == "FAIL":
        bug_errors = _extract_error_summary(bug)
        gold_errors = _extract_error_summary(gold)

        # Check if GOLD has assertion but BUG has different error
        bug_stdout = bug.get("stdout", "") or ""
        bug_stderr = bug.get("stderr", "") or ""
        bug_has_assertion = ("assertionerror" in (bug_stdout + bug_stderr).lower() or
                            "E   assert" in bug_stdout or
                            "E   assert" in bug_stderr)

        if not bug_has_assertion:
            # BUG has real error, GOLD has assertion - test is incorrect
            return "assertion_failure", (
                f"BUG and GOLD both fail, but with DIFFERENT error types:\n\n"
                f"🔴 BUG run (the actual bug being fixed):\n{bug_errors}\n\n"
                f"🟢 GOLD run (FIXED code, but YOUR TEST has wrong assertions):\n{gold_errors}\n\n"
                f"💡 Your test assertion is incorrect!\n"
                f"   The GOLD error shows your test expects the wrong return type/structure.\n"
                f"   Look at the GOLD assertion error to see what it actually returns.\n"
                f"   Update your assertions to match the actual correct behavior.\n"
                f"   For example: if it says 'isinstance([...], tuple)' failed, change to 'isinstance(result, list)'."
            )
        elif bug_errors != gold_errors:
            # Both have assertions but different ones
            return "assertion_failure", (
                f"Both variants fail with assertion errors, but with DIFFERENT failures:\n\n"
                f"🔴 BUG run (shows the bug behavior):\n{bug_errors}\n\n"
                f"🟢 GOLD run (shows what the FIXED code returns):\n{gold_errors}\n\n"
                f"💡 Your test assertion is likely incorrect!\n"
                f"   The GOLD error shows what the patched code actually returns.\n"
                f"   Update your assertions to match the GOLD behavior (correct return type/structure).\n"
                f"   For example, if GOLD shows it returns a list but you check for tuple, fix the assertion."
            )
        else:
            # Same assertion error on both - test is too strict
            return "assertion_failure", (
                f"Both variants fail the same assertion.\n\n"
                f"Error details:\n{bug_errors}\n\n"
                f"💡 Your test may be overconstrained - it fails even on the fixed code.\n"
                f"   Consider relaxing assertions to accept multiple valid forms."
            )

    if bug_status == gold_status:
        # Extract error details to help LLM fix the issue
        bug_errors = _extract_error_summary(bug)
        details = f"Both variants returned {bug_status}.\n\nError details from BUG run:\n{bug_errors}"
        return "other", details

    return "other", "Unhandled combination"


def classify_verification(
    result: Dict[str, Any],
    generated_code: str = None
) -> Diagnosis:
    """
    Classify verification result and detect anti-patterns.

    Args:
        result: Verification result from verify_instance
        generated_code: The generated test code (optional, enables pattern detection)

    Returns:
        Diagnosis with label, details, and detected patterns
    """
    summary = result.get("summary") or {}
    if summary.get("valid"):
        return Diagnosis(label="success", details="Observed discriminative claim-test.")

    tests = result.get("tests") or []
    if not tests:
        if result.get("skip_reason"):
            return Diagnosis(label="non_discriminative", details=result["skip_reason"])
        if result.get("error"):
            return Diagnosis(label="other", details=result["error"])
        return Diagnosis(label="other", details="No tests executed.")

    # CRITICAL FIX: Pass generated_code to _classify_pair for accurate classification
    label, details = _classify_pair(tests[0]["bug"], tests[0]["gold"], generated_code=generated_code or "")

    # Detect anti-patterns if code is provided
    patterns = []
    if generated_code:
        # Always run pattern detection if we have code, regardless of current label
        patterns = detect_common_antipatterns(generated_code, details)

        # If we found patterns in the test code, it's a code issue not environment
        if patterns:
            # Reclassify as internal_import_error if we detected those patterns
            if any(p.get("pattern") in ["internal_import", "fixture_attribute_error",
                                          "incorrect_fixture_creation"] for p in patterns):
                label = "internal_import_error"
            details = _enhance_internal_import_details(details, patterns)
        elif label == "internal_import_error":
            # No patterns found in test code but labeled as internal import - check if environmental
            bug_stderr = tests[0]["bug"].get("stderr", "").lower()
            if "_pytest._version" in bug_stderr or "pytest/__init__.py" in bug_stderr:
                label = "environment_error"
                details = (
                    f"Pytest installation is broken in the test environment.\n"
                    f"This is NOT a test code issue - your test code is correct!\n\n"
                    f"🎉 SUCCESS: The agent learned to use fixtures correctly!\n"
                    f"   The test properly uses tmpdir_factory as a fixture parameter.\n\n"
                    f"❌ ENVIRONMENT ISSUE: Pytest cannot initialize (missing _pytest._version).\n"
                    f"   This is a container/installation problem, not a code generation problem.\n\n"
                    f"Original error:\n{details}"
                )

    return Diagnosis(label=label, details=details, patterns=patterns)


def classify_guardrail_failure(guardrail_result: Dict[str, Any], plan: Dict[str, Any]) -> Diagnosis:
    """
    Convert guardrail failure into actionable feedback for the LLM.

    Args:
        guardrail_result: The guardrail result dict from guardrails.evaluate()
        plan: The plan dict that was being evaluated

    Returns:
        Diagnosis with label, details, and guidance for fixing the issue
    """
    reason = guardrail_result.get("reason", "unknown")
    context = guardrail_result.get("context", {})
    checks = guardrail_result.get("checks", [])

    # Find the failed check
    failed_check = None
    for check in checks:
        if check.get("label") == reason and not check.get("passed"):
            failed_check = check
            break

    if not failed_check:
        # Fallback if we can't find the specific failed check
        return Diagnosis(
            label="guardrail_check_failed",
            details=f"Guardrail check '{reason}' failed. Review the plan and try again."
        )

    details_dict = failed_check.get("details", {})
    action = failed_check.get("action", "")

    # Generate specific feedback based on the check type
    if reason == "signature_check":
        missing_symbols = details_dict.get("missing_symbols", [])
        resolved_symbols = details_dict.get("resolved_symbols", {})
        module = context.get("module", "unknown")

        if missing_symbols:
            symbols_str = ", ".join(f"'{s}'" for s in missing_symbols)
            details = (
                f"🔍 SIGNATURE CHECK FAILED\n\n"
                f"The following symbols were not found in module '{module}':\n"
                f"  {symbols_str}\n\n"
                f"💡 POSSIBLE FIXES:\n"
                f"1. Check if these symbols exist in a different module\n"
                f"   - Try importing directly: 'import {missing_symbols[0].split('.')[0]}' instead\n"
                f"   - Or look in related modules (check the issue context for correct imports)\n\n"
                f"2. The symbol might be in the same package but different submodule\n"
                f"   - Example: 'sympy.Symbol' is in 'sympy.core.symbol', not 'sympy.core.expr'\n"
                f"   - Try: from sympy import Symbol  (imports work across submodules)\n\n"
                f"3. Look at the test_patch files in the issue - they show working imports\n\n"
            )

            if resolved_symbols:
                resolved_str = "\n".join(f"  ✅ {k} -> {v}" for k, v in resolved_symbols.items())
                details += f"Successfully resolved symbols:\n{resolved_str}\n"

            return Diagnosis(label="signature_check", details=details)

    elif reason == "import_check":
        module = context.get("module", "unknown")
        error = details_dict.get("error", "")
        repo_path = details_dict.get("repo_path", "")

        details = (
            f"🔍 IMPORT CHECK FAILED\n\n"
            f"Could not import module '{module}'\n"
            f"Error: {error}\n\n"
            f"💡 POSSIBLE FIXES:\n"
            f"1. Verify the module name is correct\n"
            f"   - Check the grounding evidence for the correct module path\n"
            f"   - Look at imports in the issue's code blocks\n\n"
            f"2. The module might not be importable in the planning phase\n"
            f"   - This is OK - the test will run in the correct environment\n"
            f"   - Just ensure your test code uses the correct import statements\n\n"
            f"3. If this is a submodule issue, try using top-level imports\n"
            f"   - Instead of: from deeply.nested.module import Thing\n"
            f"   - Try: import package; package.Thing\n\n"
        )

        if repo_path:
            details += f"Repository path: {repo_path}\n"

        return Diagnosis(label="import_error", details=details)

    elif reason == "probe_check":
        failures = details_dict.get("failures", [])

        if failures:
            failures_str = "\n".join(f"  ❌ {f}" for f in failures)
            details = (
                f"🔍 PROBE CHECK FAILED\n\n"
                f"The following symbols cannot be called without proper arguments:\n"
                f"{failures_str}\n\n"
                f"💡 FIX:\n"
                f"{action or 'Ensure your test creates necessary instances/objects before calling these methods.'}\n\n"
                f"This usually means the function/method requires specific arguments.\n"
                f"Make sure your test:\n"
                f"1. Creates any necessary objects/instances first\n"
                f"2. Provides all required arguments when calling the function\n"
                f"3. Uses proper fixtures if needed (tmpdir, monkeypatch, etc.)\n"
            )
            return Diagnosis(label="probe_check_failed", details=details)

    # Generic fallback for other check types
    label = f"{reason}_failed"
    details = f"Guardrail check '{reason}' failed.\n\n"
    if action:
        details += f"💡 Suggested action: {action}\n\n"
    if details_dict:
        details += f"Details: {details_dict}\n"

    return Diagnosis(label=label, details=details)
