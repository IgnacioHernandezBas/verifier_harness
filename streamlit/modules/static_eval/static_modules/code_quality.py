"""
Code quality verifier for Python projects.
│
├─ (1) Gather modified python files from a given patch
│
├─ (2) Get overall score Pylint
│     → Runs pylint on each modified Python file
│
├─ (3) Flake8 checks the code style follows PEP8 standards
│   
├─ (4) Radon for complexity and maintainability
│     → Cyclomatic complexity per 
│     → Maintainability Index (MI) per file
│
├─ (5)Mypy for type checking
│    → Type errors per file
│
├─ (6) Bandit for security issues
│    → Security issues per file
│
└─ (7) Aggregate results into a Static Quality Index (SQI) and return detailed report




"""
import os, sys, re, json, subprocess, numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional
from radon.complexity import cc_visit
from radon.metrics import mi_visit

# -------------------------------
# Default configuration constants
# -------------------------------
DEFAULT_CHECKS = {
    "pylint": True,
    "flake8": True,
    "radon": True,
    "mypy": True,
    "bandit": True,
}

DEFAULT_WEIGHTS = {
    "pylint": 0.5,
    "radon": 0.25,
    "flake8": 0.15,
    "mypy": 0.05,
    "bandit": 0.05,
}

# -------------------------------
# Dynamic import setup
# -------------------------------
CURRENT_DIR = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_DIR.parents[2]
sys.path.append(str(PROJECT_ROOT))

#from modules.loading.dataset_loader import DatasetLoader
#from modules.loading.patch_loader import PatchLoader
from modules.utils.diff_utils import parse_unified_diff, filter_paths_to_py


# -----------------------
# (1) Gather modified Python files
# -----------------------
def get_modified_files(repo_path: str, patch_str: str) -> List[str]:
    """Use diff_utils to extract modified Python files with absolute paths."""
    parsed = parse_unified_diff(patch_str)
    rel_paths = filter_paths_to_py(list(parsed.keys()))
    abs_paths = [
        os.path.join(repo_path, rel_path)
        for rel_path in rel_paths
        if os.path.exists(os.path.join(repo_path, rel_path))
    ]
    return abs_paths


# -----------------------
# (2) Pylint — overall quality and issues
# -----------------------
def run_pylint(file_path: str) -> dict:
    """
    Run Pylint using the official API and retrieve both JSON results and the numeric score.
    """
    from pylint.lint import Run
    from pylint.reporters.json_reporter import JSONReporter
    from io import StringIO
    import json

    buffer = StringIO()
    reporter = JSONReporter(output=buffer)

    # Run Pylint on the given file without exiting the process
    results = Run([file_path], reporter=reporter, exit=False)

    # Parse structured JSON messages
    buffer.seek(0)
    messages = json.loads(buffer.read() or "[]")

    # Access the overall score directly
    score = results.linter.stats.global_note or 0.0

    # Collect issue list
    issues = []
    for msg in messages:
        issues.append({
            "type": msg.get("type"),
            "symbol": msg.get("symbol"),
            "line": msg.get("line"),
            "message": msg.get("message"),
            "message_id": msg.get("message-id"),
        })

    return {"score": round(score, 2), "issues": issues}


# -----------------------
# (3) Flake8 — style and PEP8 compliance
# -----------------------
def run_flake8(file_path: str) -> List[Dict]:
    """Run flake8 on a single file and return the list of style issues."""
    try:
        result = subprocess.run(
            ["flake8", file_path, "--format=json"],
            capture_output=True,
            text=True,
            check=False,  # non-zero exit = warnings found
        )
        flake8_data = json.loads(result.stdout or "{}")
        issues = []
        for file_issues in flake8_data.values():
            for issue in file_issues:
                issues.append({
                    "line": issue.get("line_number"),
                    "code": issue.get("code"),
                    "message": issue.get("text"),
                })
        return issues
    except json.JSONDecodeError:
        print(f"⚠️ Could not parse flake8 JSON for {file_path}")
        return []
    except Exception as e:
        print(f"Flake8 failed for {file_path}: {e}")
        return []


# -----------------------
# (4) Radon — complexity and maintainability
# https://radon.readthedocs.io/en/latest/intro.html
# -----------------------

def run_radon_complexity(file_path: str) -> List[Dict]:
    """Run Radon cyclomatic complexity analysis (per function)."""
    try:
        result = subprocess.run(
            ["radon", "cc", "-s", "-j", file_path],
            capture_output=True,
            text=True,
            check=False,
        )
        cc_data = json.loads(result.stdout or "{}")
        return [
            {"name": func.get("name"), "complexity": func.get("complexity"), "lineno": func.get("lineno")}
            for func in cc_data.get(file_path, [])
        ]
    except Exception as e:
        print(f"Radon CC failed for {file_path}: {e}")
        return []


def run_radon_mi(file_path: str) -> float:
    """Compute Radon Maintainability Index (MI) for a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        mi = mi_visit(code, True)  # True → return as numeric float
        return round(mi, 2)
    except Exception as e:
        print(f"Radon MI failed for {file_path}: {e}")
        return 0.0
# -----------------------
# (5) Mypy - type checking
# -----------------------   
    
def run_mypy(file_path: str) -> List[Dict]:
    """
    Run Mypy on a Python file or directory and parse structured results.

    Works on both Windows and Unix-like paths (handles 'C:\\' safely).

    Args:
        file_path (str): Path to a Python file or folder.

    Returns:
        List[Dict]: Parsed Mypy issues.
    """
    if not os.path.exists(file_path):
        return []

    issues = []

    try:
        result = subprocess.run(
            ["mypy", "--show-column-numbers", "--show-error-codes", file_path],
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout.strip()
        if not output:
            return []

        for raw_line in output.splitlines():
            if not raw_line.strip():
                continue

            # Handle Windows drive letters safely: e.g., "C:\"
            if os.name == "nt" and len(raw_line) > 2 and raw_line[1:3] == ":\\":
                drive = raw_line[:3]  # "C:\"
                rest = raw_line[3:]
                parts = rest.split(":", 4)
                parts[0] = drive + parts[0]
            else:
                parts = raw_line.split(":", 4)

            filename = parts[0].strip() if len(parts) > 0 else None

            # Extract line and column numbers
            try:
                line_number = int(parts[1].strip()) if len(parts) > 1 else None
            except ValueError:
                line_number = None

            try:
                column = int(parts[2].strip()) if len(parts) > 2 else None
            except ValueError:
                column = None

            # Extract severity and message
            lower_line = raw_line.lower()
            if "error:" in lower_line:
                severity = "error"
                message = raw_line.split("error:", 1)[1].strip()
            elif "note:" in lower_line:
                severity = "note"
                message = raw_line.split("note:", 1)[1].strip()
            else:
                severity = "info"
                message = raw_line.split(":", 3)[-1].strip()

            # Extract error code in square brackets
            error_code = None
            if "[" in message and "]" in message:
                start = message.rfind("[")
                end = message.rfind("]")
                if end > start:
                    error_code = message[start + 1:end]
                    message = message[:start].strip()

            issues.append({
                "filename": filename,
                "line_number": line_number,
                "column": column,
                "severity": severity,
                "message": message,
                "error_code": error_code
            })

    except Exception as e:
        issues.append({
            "filename": file_path,
            "line_number": None,
            "column": None,
            "severity": "internal_error",
            "message": f"Failed to run mypy: {e}",
            "error_code": None
        })

    return issues
        
# -----------------------
# (6) Bandit - security issues 
# -----------------------

def run_bandit(file_path: str) -> List[Dict]:
    """
    Run Bandit security scanner and return detailed results.
    
    Args:
        file_path (str): Path to the Python file to scan
        
    Returns:
        list: List of security issues with detailed information
    """
    import subprocess
    import json
    import tempfile
    
    if not os.path.exists(file_path) or not file_path.endswith('.py'):
        return []
    
    issues = []
    
    try:
        # Create temporary file for JSON output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        # Run bandit with JSON output format
        # Note: bandit returns exit code 1 when issues are found, so we don't use check=True
        result = subprocess.run(
            ['bandit', '-f', 'json', '-o', tmp_path, file_path],
            capture_output=True,
            text=True
        )
        
        # Read JSON output
        if os.path.exists(tmp_path):
            with open(tmp_path, 'r', encoding='utf-8') as f:
                bandit_output = json.load(f)
            
            # Extract results
            for issue in bandit_output.get('results', []):
                issues.append({
                    'filename': issue.get('filename', file_path),
                    'line_number': issue.get('line_number'),
                    'line_range': issue.get('line_range', []),
                    'code': issue.get('code', '').strip(),
                    'test_id': issue.get('test_id'),
                    'test_name': issue.get('test_name'),
                    'issue_severity': issue.get('issue_severity'),
                    'issue_confidence': issue.get('issue_confidence'),
                    'issue_text': issue.get('issue_text'),
                    'issue_cwe': issue.get('issue_cwe'),
                    'more_info': issue.get('more_info')
                })
            
            # Clean up temp file
            os.unlink(tmp_path)
    
    except Exception as e:
        print(f"Error running bandit on {file_path}: {e}")
    
    return issues

def compute_sqi(
    pylint_score: float,
    radon_mi: float,
    flake8_issues: list,
    mypy_errors: int,
    bandit_counts: dict,
    loc: int,
    weights: Optional[Dict[str,Any]]= None,
    checks: Optional[Dict[str,Any]] = None,
) -> dict:
    """
    Compute Static Quality Index (SQI) combining enabled static analyzers.
    Automatically renormalizes weights based on which checks are active.
    """
    from math import isclose

    weights = weights or DEFAULT_WEIGHTS
    checks = checks or DEFAULT_CHECKS

    # Filter to active tools
    active_weights = {k: v for k, v in weights.items() if checks.get(k, True)}

    # Renormalize so they sum to 1
    total = sum(active_weights.values())
    if total == 0 or isclose(total, 0.0):
        active_weights = {k: 1 / len(active_weights) for k in active_weights}
    else:
        active_weights = {k: v / total for k, v in active_weights.items()}

    # --- Normalize submetrics ---
    pylint_norm = max(0.0, min(100.0, (pylint_score / 10) * 100)) if checks.get("pylint", True) else 0
    radon_norm = max(0.0, min(100.0, radon_mi)) if checks.get("radon", True) else 0

    if loc == 0:
        flake8_norm = 100.0
    elif checks.get("flake8", True):
        weights_f8 = {"F": 3.0, "E": 1.0, "W": 0.5, "C": 0.8, "N": 0.8, "D": 0.8}
        weighted_sum = sum(weights_f8.get(i["code"][0], 1.0) for i in flake8_issues)
        penalty = min(1.0, weighted_sum / (loc * 0.5))
        flake8_norm = max(0.0, (1 - penalty) * 100)
    else:
        flake8_norm = 0

    if checks.get("mypy", True):
        gamma = 50
        mypy_norm = max(0.0, (1 - (mypy_errors / (gamma + max(loc, 1)))) * 100)
    else:
        mypy_norm = 0

    if checks.get("bandit", True):
        beta = 10
        wB = {"HIGH": 5, "MEDIUM": 3, "LOW": 1}
        weighted_bandit = sum(wB[k] * v for k, v in bandit_counts.items())
        bandit_norm = max(0.0, (1 - (weighted_bandit / beta)) * 100)
    else:
        bandit_norm = 0

    # --- Weighted aggregation ---
    sqi = 0.0
    for key, w in active_weights.items():
        if key == "pylint": sqi += w * pylint_norm
        elif key == "radon": sqi += w * radon_norm
        elif key == "flake8": sqi += w * flake8_norm
        elif key == "mypy": sqi += w * mypy_norm
        elif key == "bandit": sqi += w * bandit_norm

    # --- Classification ---
    if sqi >= 85:
        label = "Excellent"
    elif sqi >= 70:
        label = "Good"
    elif sqi >= 50:
        label = "Fair"
    else:
        label = "Poor"

    return {
        "SQI": round(sqi, 2),
        "classification": label,
        "components": {
            "pylint": round(pylint_norm, 2),
            "radon": round(radon_norm, 2),
            "flake8": round(flake8_norm, 2),
            "mypy": round(mypy_norm, 2),
            "bandit": round(bandit_norm, 2),
        },
        "weights_used": active_weights,
    }



def analyze(repo_path: str, patch_str: str, config: Optional[Dict[str, Any]] = None) -> Dict:
    """
    Analyze only the patch-modified files using the selected static analyzers.

    Args:
        repo_path (str): Local path to the repository under analysis.
        patch_str (str): Unified diff string representing the patch.
        config optional dic: Configuration dictionary with:
            - checks: Dict[str, bool] → which analyzers to enable
            - weights: Dict[str, float] → weighting for SQI computation
    Returns:
        Dict: Structured report containing results for all enabled analyzers and SQI.
    """
    # Configuration set up
    config = config or {}
    checks = config.get("checks", DEFAULT_CHECKS)
    weights = config.get("weights", DEFAULT_WEIGHTS)

    modified_files = get_modified_files(repo_path, patch_str)
    if not modified_files:
        return {"error": "No modified Python files detected."}

    # Initialize result containers
    pylint_scores = []
    pylint_issues = {}
    flake8_all = []
    radon_complexities = {}
    radon_mis = []
    mypy_issues = []  # Changed: Now collecting detailed issues
    bandit_issues = []
    total_loc = 0

    # Run analyzers on each modified file
    for file_path in modified_files:

        # ---- Pylint ----
        if checks.get("pylint", True):
            pylint_result = run_pylint(file_path)
            pylint_scores.append(pylint_result["score"])
            pylint_issues[file_path] = pylint_result["issues"]

        # ---- Flake8 ----
        if checks.get("flake8", True):
            issues = run_flake8(file_path)
            flake8_all.extend(issues)

        # ---- Radon ----
        if checks.get("radon", True):
            radon_complexities[file_path] = run_radon_complexity(file_path)
            radon_mis.append(run_radon_mi(file_path))

        # ---- Mypy ----
        if checks.get("mypy", True):
            mypy_res = run_mypy(file_path)  # Now returns list of detailed issues
            mypy_issues.extend(mypy_res)

        # ---- Bandit ----
        if checks.get("bandit", True):
            bandit_res = run_bandit(file_path)
            bandit_issues.extend(bandit_res)

        # ---- LOC count ----
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                total_loc += len(f.readlines())
        except Exception:
            pass
        
    # Compute aggregated metrics    
    avg_pylint = sum(pylint_scores) / len(pylint_scores) if pylint_scores else 0.0
    avg_mi = sum(radon_mis) / len(radon_mis) if radon_mis else 0.0

    # Convert bandit detailed issues to counts for SQI computation
    bandit_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for issue in bandit_issues:
        severity = issue.get('issue_severity', 'MEDIUM').upper()
        if severity in bandit_counts:
            bandit_counts[severity] += 1
    
    # Count mypy errors for SQI computation
    mypy_error_count = len([issue for issue in mypy_issues if issue.get('severity') == 'error'])
    
    # Compute SQI with active weights and checks
    sqi_result = compute_sqi(
        pylint_score=avg_pylint,
        radon_mi=avg_mi,
        flake8_issues=flake8_all,
        mypy_errors=mypy_error_count,  # Use count for SQI
        bandit_counts=bandit_counts,
        loc=total_loc,
        weights=weights,
        checks=checks,
    )

    # Aggregate results in unified dictionary
    results = {
        "modified_files": modified_files,
        "sqi": sqi_result,
        "active_checks": {k: v for k, v in checks.items() if v},
        "pylint": pylint_issues if checks.get("pylint", True) else None,
        "flake8": flake8_all if checks.get("flake8", True) else None,
        "radon": {
            "complexity": radon_complexities if checks.get("radon", True) else None,
            "mi_avg": avg_mi if checks.get("radon", True) else None,
        },
        "mypy": mypy_issues if checks.get("mypy", True) else None,  # Return detailed issues
        "bandit": bandit_issues if checks.get("bandit", True) else None,
        "meta": {
            "total_loc": total_loc,
            "n_files": len(modified_files),
        },
    }

    return results


