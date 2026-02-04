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


def _classify_pair(bug: Dict[str, Any], gold: Dict[str, Any]) -> Tuple[str, str]:
    bug_status = bug.get("status")
    gold_status = gold.get("status")
    combined = f"{_collect_outputs(bug)}\n{_collect_outputs(gold)}"

    if bug_status == "PASS" and gold_status == "PASS":
        return "non_discriminative", "Both variants pass. Claim may not capture bug."

    if "importerror" in combined or "module not found" in combined:
        return "import_error", "Import failed while running the test."

    if "missing 1 required positional argument" in combined or "missing required positional argument" in combined:
        return "signature_mismatch", "Call signature mismatch."

    if "fixture" in combined and "missing" in combined:
        return "fixture_missing", "Fixtures or inputs missing."

    if "assertionerror" in combined and bug_status == gold_status == "FAIL":
        return "assertion_failure", "Both variants fail the same assertion."

    if bug_status == gold_status:
        return "other", f"Both variants returned {bug_status}."

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
