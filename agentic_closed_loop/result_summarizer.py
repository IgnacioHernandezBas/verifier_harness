#!/usr/bin/env python3
"""
Result summarizer for agentic loop runs.

Creates human-readable and machine-readable summaries of test generation results.
Organized by test generation model and claim extraction model.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from common.model_paths import slugify_model_name


def create_result_summary(
    state_file: Path,
    tests_model: str,
    claims_model: Optional[str] = None,
    slurm_job_id: Optional[str] = None,
    results_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Create summary files from a state file.

    Args:
        state_file: Path to the state JSON file
        tests_model: Model used for test generation
        claims_model: Model used for claim extraction (defaults to tests_model)
        slurm_job_id: SLURM job ID for reference
        results_root: Root directory for results (defaults to agentic_closed_loop/results)

    Returns:
        Summary dictionary
    """
    if not state_file.exists():
        raise FileNotFoundError(f"State file not found: {state_file}")

    state = json.loads(state_file.read_text())

    # Extract basic info
    instance_id = state.get("instance_id", "unknown")
    claim_id = state.get("claim_id", "C1")
    attempts = state.get("attempts", [])

    # Determine status and final result
    status, final_result, failure_reason = _determine_status(state, attempts)

    # Build iteration history
    iterations = _build_iteration_history(attempts)

    # Determine output paths
    if results_root is None:
        results_root = state_file.parent.parent / "results"

    tests_slug = slugify_model_name(tests_model)
    claims_slug = slugify_model_name(claims_model or tests_model)

    summary_dir = results_root / f"tests_{tests_slug}" / f"claims_{claims_slug}"
    summary_dir.mkdir(parents=True, exist_ok=True)

    # Build summary
    summary = {
        "instance_id": instance_id,
        "claim_id": claim_id,
        "timestamp": datetime.now().isoformat(),
        "slurm_job_id": slurm_job_id or os.getenv("SLURM_JOB_ID", "unknown"),
        "models": {
            "tests_model": tests_model,
            "claims_model": claims_model or tests_model,
        },
        "status": status,
        "total_attempts": len(attempts),
        "max_attempts": state.get("max_attempts", len(attempts)),
        "final_result": final_result,
        "failure_reason": failure_reason,
        "iterations": iterations,
        "files": {
            "state_file": str(state_file),
            "test_file": _get_test_file_path(state, attempts),
            "slurm_logs": _get_slurm_log_paths(slurm_job_id),
        },
    }

    # Write JSON summary
    json_path = summary_dir / f"{instance_id}_{claim_id}_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # Write text summary
    txt_path = summary_dir / f"{instance_id}_{claim_id}_summary.txt"
    txt_path.write_text(_format_text_summary(summary))

    # Update CSV aggregate
    _update_csv_summary(results_root, summary)

    print(f"✓ Results summary written to: {summary_dir}")
    print(f"  - {json_path.name}")
    print(f"  - {txt_path.name}")

    return summary


def _determine_status(
    state: Dict[str, Any], attempts: list[Dict[str, Any]]
) -> tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    """Determine overall status and final results."""
    if not attempts:
        return "no_attempts", None, "No attempts recorded"

    last_attempt = attempts[-1]

    # Check for success
    verification = last_attempt.get("verification_result", {})
    if verification:
        tests = verification.get("tests", [])
        if tests:
            test_result = tests[0]  # First test
            classification = test_result.get("classification", {})
            label = classification.get("label", "")

            if label == "VALID":
                bug_status = test_result.get("bug", {}).get("status", "UNKNOWN")
                gold_status = test_result.get("gold", {}).get("status", "UNKNOWN")
                return "success", {
                    "discriminative": True,
                    "classification": label,
                    "bug": bug_status,
                    "gold": gold_status,
                }, None
            elif label == "NON_DISCRIMINATIVE":
                bug_status = test_result.get("bug", {}).get("status", "UNKNOWN")
                gold_status = test_result.get("gold", {}).get("status", "UNKNOWN")
                return "non_discriminative", {
                    "discriminative": False,
                    "classification": label,
                    "bug": bug_status,
                    "gold": gold_status,
                }, "Test does not discriminate between bug and gold"
            elif label in ["OVERCONSTRAINED", "INVERTED", "UNRESOLVED"]:
                bug_status = test_result.get("bug", {}).get("status", "UNKNOWN")
                gold_status = test_result.get("gold", {}).get("status", "UNKNOWN")
                return "failed", {
                    "discriminative": False,
                    "classification": label,
                    "bug": bug_status,
                    "gold": gold_status,
                }, f"Classification: {label}"

    # Check for guardrail failures
    if last_attempt.get("status") == "guardrail_failed":
        failure_class = last_attempt.get("failure_classification", {})
        label = failure_class.get("label", "unknown_error")
        details = failure_class.get("details", "")
        return "guardrail_failed", None, f"{label}: {details}" if details else label

    # Check exit reason from state
    exit_reason = state.get("exit_reason")
    if exit_reason:
        if "max_attempts" in exit_reason:
            return "max_attempts", None, "Maximum attempts reached without success"
        if "stuck_in_loop" in exit_reason:
            return "stuck", None, exit_reason

    # Check failure classification
    failure_class = last_attempt.get("failure_classification", {})
    if failure_class:
        label = failure_class.get("label", "unknown")
        details = failure_class.get("details", "")
        return "failed", None, f"{label}: {details}" if details else label

    return "unknown", None, "Unable to determine status"


def _build_iteration_history(attempts: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Build a simplified iteration history."""
    history = []

    for attempt in attempts:
        attempt_num = attempt.get("attempt", len(history) + 1)
        status = attempt.get("status", "unknown")

        entry = {
            "attempt": attempt_num,
            "status": status,
        }

        # Add status-specific details
        if status == "guardrail_failed":
            failure = attempt.get("failure_classification", {})
            entry["issue"] = f"{failure.get('label', 'unknown')}: {failure.get('details', '')}"
        elif status == "verification_complete":
            verification = attempt.get("verification_result", {})
            tests = verification.get("tests", [])
            if tests:
                test = tests[0]
                classification = test.get("classification", {})
                label = classification.get("label", "UNKNOWN")
                entry["classification"] = label
                entry["bug"] = test.get("bug", {}).get("status", "UNKNOWN")
                entry["gold"] = test.get("gold", {}).get("status", "UNKNOWN")

                if label == "VALID":
                    entry["status"] = "success"
                else:
                    entry["issue"] = classification.get("reason", label)
        else:
            failure = attempt.get("failure_classification", {})
            if failure:
                entry["issue"] = f"{failure.get('label', '')}: {failure.get('details', '')}"

        history.append(entry)

    return history


def _get_test_file_path(state: Dict[str, Any], attempts: list[Dict[str, Any]]) -> Optional[str]:
    """Extract the test file path from attempts."""
    for attempt in reversed(attempts):
        test_path = attempt.get("generated_test_path")
        if test_path:
            return test_path
    return None


def _get_slurm_log_paths(job_id: Optional[str]) -> Dict[str, str]:
    """Get SLURM log file paths."""
    if not job_id or job_id == "unknown":
        return {}

    base = Path("agentic_closed_loop/scripts_slurm/logs")
    return {
        "out": str(base / f"agentic_hybrid_{job_id}.out"),
        "err": str(base / f"agentic_hybrid_{job_id}.err"),
        "vllm": str(base / f"vllm_hybrid_{job_id}.log"),
    }


def _format_text_summary(summary: Dict[str, Any]) -> str:
    """Format a human-readable text summary."""
    status = summary["status"]
    instance_id = summary["instance_id"]
    claim_id = summary["claim_id"]

    # Status symbol
    status_symbols = {
        "success": "✓ SUCCESS",
        "non_discriminative": "✗ NON-DISCRIMINATIVE",
        "failed": "✗ FAILED",
        "guardrail_failed": "⚠ GUARDRAIL FAILED",
        "max_attempts": "⚠ MAX ATTEMPTS",
        "stuck": "⚠ STUCK",
        "unknown": "? UNKNOWN",
        "no_attempts": "- NO ATTEMPTS",
    }
    status_display = status_symbols.get(status, f"? {status.upper()}")

    lines = [
        "=" * 80,
        "AGENTIC LOOP SUMMARY",
        "=" * 80,
        f"Instance:       {instance_id}",
        f"Claim:          {claim_id}",
        f"Tests Model:    {summary['models']['tests_model']}",
        f"Claims Model:   {summary['models']['claims_model']}",
        f"Timestamp:      {summary['timestamp']}",
        f"SLURM Job:      {summary.get('slurm_job_id', 'N/A')}",
        "",
        f"STATUS:         {status_display}",
        f"Attempts:       {summary['total_attempts']} / {summary['max_attempts']}",
        "",
    ]

    # Add final results if available
    final = summary.get("final_result")
    if final:
        lines.append("FINAL RESULTS:")
        lines.append(f"  Classification: {final.get('classification', 'N/A')}")
        lines.append(f"  Bug:            {final.get('bug', 'N/A')}")
        lines.append(f"  Gold:           {final.get('gold', 'N/A')}")
        lines.append(f"  Discriminative: {'YES' if final.get('discriminative') else 'NO'}")
        lines.append("")

    # Add failure reason if present
    if summary.get("failure_reason"):
        lines.append(f"FAILURE REASON: {summary['failure_reason']}")
        lines.append("")

    # Add iteration history
    iterations = summary.get("iterations", [])
    if iterations:
        lines.append("ITERATION HISTORY:")
        for it in iterations:
            attempt = it.get("attempt", "?")
            status = it.get("status", "unknown").upper()

            if status == "SUCCESS":
                lines.append(f"  [{attempt}] ✓ SUCCESS")
                lines.append(f"      Bug={it.get('bug', '?')}, Gold={it.get('gold', '?')}")
            elif "issue" in it:
                lines.append(f"  [{attempt}] {status}")
                lines.append(f"      {it['issue']}")
            else:
                lines.append(f"  [{attempt}] {status}")
                if "classification" in it:
                    lines.append(f"      {it['classification']}: Bug={it.get('bug', '?')}, Gold={it.get('gold', '?')}")
            lines.append("")

    # Add file references
    lines.append("FILES:")
    test_file = summary["files"].get("test_file")
    if test_file:
        lines.append(f"  Test:         {test_file}")
    lines.append(f"  State:        {summary['files']['state_file']}")
    slurm_logs = summary["files"].get("slurm_logs", {})
    if slurm_logs:
        lines.append(f"  SLURM logs:   {slurm_logs.get('out', 'N/A')}")
        lines.append(f"                {slurm_logs.get('err', 'N/A')}")
    lines.append("=" * 80)

    return "\n".join(lines)


def _update_csv_summary(results_root: Path, summary: Dict[str, Any]) -> None:
    """Update or create aggregate CSV summary."""
    csv_path = results_root / "summary_report.csv"

    # Prepare row
    final = summary.get("final_result") or {}
    row = {
        "instance_id": summary["instance_id"],
        "claim_id": summary["claim_id"],
        "tests_model": summary["models"]["tests_model"],
        "claims_model": summary["models"]["claims_model"],
        "status": summary["status"],
        "discriminative": final.get("discriminative", False),
        "classification": final.get("classification", "N/A"),
        "attempts": summary["total_attempts"],
        "bug": final.get("bug", "N/A"),
        "gold": final.get("gold", "N/A"),
        "failure_reason": summary.get("failure_reason", ""),
        "timestamp": summary["timestamp"],
        "slurm_job_id": summary.get("slurm_job_id", ""),
    }

    # Read existing CSV or create new
    fieldnames = list(row.keys())
    existing_rows = []

    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)

    # Update or append
    updated = False
    for i, existing_row in enumerate(existing_rows):
        if (existing_row.get("instance_id") == row["instance_id"] and
            existing_row.get("claim_id") == row["claim_id"] and
            existing_row.get("tests_model") == row["tests_model"] and
            existing_row.get("claims_model") == row["claims_model"]):
            existing_rows[i] = row
            updated = True
            break

    if not updated:
        existing_rows.append(row)

    # Write CSV
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_rows)


def main():
    """CLI entry point for standalone usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate result summaries from state files")
    parser.add_argument("--state-file", type=Path, required=True, help="Path to state JSON file")
    parser.add_argument("--tests-model", required=True, help="Model used for test generation")
    parser.add_argument("--claims-model", default=None, help="Model used for claim extraction")
    parser.add_argument("--slurm-job-id", default=None, help="SLURM job ID")
    parser.add_argument("--results-root", type=Path, default=None, help="Results root directory")

    args = parser.parse_args()

    summary = create_result_summary(
        state_file=args.state_file,
        tests_model=args.tests_model,
        claims_model=args.claims_model,
        slurm_job_id=args.slurm_job_id,
        results_root=args.results_root,
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
