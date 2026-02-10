from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Tuple


@dataclass
class Diagnosis:
    label: str
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _collect_outputs(test_run: Dict[str, Any]) -> str:
    stdout = (test_run.get("stdout") or "").lower()
    stderr = (test_run.get("stderr") or "").lower()
    return f"{stdout}\n{stderr}"


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


def _classify_pair(bug: Dict[str, Any], gold: Dict[str, Any]) -> Tuple[str, str]:
    bug_status = bug.get("status")
    gold_status = gold.get("status")
    combined = f"{_collect_outputs(bug)}\n{_collect_outputs(gold)}"

    if bug_status == "PASS" and gold_status == "PASS":
        return "non_discriminative", "Both variants pass. Claim may not capture bug."

    if "importerror" in combined or "module not found" in combined:
        bug_errors = _extract_error_summary(bug)
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

    if "fixture" in combined and "missing" in combined:
        bug_errors = _extract_error_summary(bug)
        return "fixture_missing", f"Fixtures or inputs missing.\n\nError details:\n{bug_errors}"

    if "assertionerror" in combined and bug_status == gold_status == "FAIL":
        bug_errors = _extract_error_summary(bug)
        return "assertion_failure", f"Both variants fail the same assertion.\n\nError details:\n{bug_errors}"

    if bug_status == gold_status:
        # Extract error details to help LLM fix the issue
        bug_errors = _extract_error_summary(bug)
        details = f"Both variants returned {bug_status}.\n\nError details from BUG run:\n{bug_errors}"
        return "other", details

    return "other", "Unhandled combination"


def classify_verification(result: Dict[str, Any]) -> Diagnosis:
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

    label, details = _classify_pair(tests[0]["bug"], tests[0]["gold"])
    return Diagnosis(label=label, details=details)
