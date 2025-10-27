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
from typing import Dict, List
from radon.complexity import cc_visit
from radon.metrics import mi_visit

# -------------------------------
# Dynamic import setup
# -------------------------------
CURRENT_DIR = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_DIR.parents[2]
sys.path.append(str(PROJECT_ROOT))

from swebench_integration.dataset_loader import DatasetLoader
from swebench_integration.patch_loader import PatchLoader
from verifier.utils.diff_utils import parse_unified_diff, filter_paths_to_py


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
    
def run_mypy(file_path: str,error_output:bool=False) -> Dict:
    """
    Run Mypy on a single file and return structured error information.
    Returns:
        {   
            "error_count": int,
            "errors": List[Dict[str, str]],
        }
    """
    try:
        result = subprocess.run(
            [
                "mypy",
                file_path,
                "--ignore-missing-imports",
                "--no-color-output",
                "--no-error-summary",
                "--show-error-codes",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        errors = []
        errors_without_output=0
        for line in result.stdout.splitlines():
            # Typical format: file.py:12: error: <message>  [code]
            if "error:" in line:
                parts = line.split(":", 3)
                if error_output:
                    if len(parts) >= 4:
                        line_num = parts[1]
                        msg = parts[3].strip()
                        errors.append({"file_path":file_path,"line": line_num, "message": msg})
                else:
                    errors_without_output+=1
        if error_output:
            return {
                "error_count": len(errors),
                "errors": errors
            }
        else:
            return {
                "error_count": errors_without_output 
            }   

    except Exception as e:
        print(f"Mypy failed for {file_path}: {e}")
        return {"error_count": 0, "errors": []}
        
# -----------------------
# (6) Bandit - security issues 
# -----------------------

def run_bandit(file_path: str) -> Dict[str, int]:
    """Run Bandit security scanner and return issue counts by severity."""
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-q", "-r", file_path],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout or "{}")
        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for issue in data.get("results", []):
            sev = issue.get("issue_severity", "LOW").upper()
            counts[sev] = counts.get(sev, 0) + 1
        return counts
    except Exception as e:
        print(f"Bandit failed for {file_path}: {e}")
        return {"LOW": 0, "MEDIUM": 0, "HIGH": 0}

def compute_sqi(
    pylint_score: float,
    radon_mi: float,
    flake8_issues: List[Dict],
    mypy_errors: int,
    bandit_counts: Dict[str, int],
    loc: int,
    weights: Dict[str, float] = {},
) -> Dict:
    """
    Compute Static Quality Index (SQI) combining all static analyzers.
    Each subscore is normalized to [0, 100].
    """
    weights = weights or {
        "pylint": 0.5,
        "radon": 0.25,
        "flake8": 0.15,
        "mypy": 0.05,
        "bandit": 0.05,
    }

    # --- Normalize submetrics ---
    pylint_norm = max(0.0, min(100.0, (pylint_score / 10) * 100))
    radon_norm = max(0.0, min(100.0, radon_mi))

    # Flake8 normalization (weighted per code letter)
    if loc == 0:
        flake8_norm = 100.0
    else:
        weights_f8 = {"F": 3.0, "E": 1.0, "W": 0.5, "C": 0.8, "N": 0.8, "D": 0.8}
        weighted_sum = sum(weights_f8.get(i["code"][0], 1.0) for i in flake8_issues)
        penalty = min(1.0, weighted_sum / (loc * 0.5))
        flake8_norm = max(0.0, (1 - penalty) * 100)

    # Mypy normalization
    gamma = 50  # type-tolerance constant
    mypy_norm = max(0.0, (1 - (mypy_errors / (gamma + max(loc, 1)))) * 100)

    # Bandit normalization
    beta = 10  # security tolerance threshold
    wB = {"HIGH": 5, "MEDIUM": 3, "LOW": 1}
    weighted_bandit = sum(wB[k] * v for k, v in bandit_counts.items())
    bandit_norm = max(0.0, (1 - (weighted_bandit / beta)) * 100)

    # --- Weighted aggregation ---
    sqi = (
        weights["pylint"] * pylint_norm +
        weights["radon"] * radon_norm +
        weights["flake8"] * flake8_norm +
        weights["mypy"] * mypy_norm +
        weights["bandit"] * bandit_norm
    )

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
    }



# -----------------------
# (6) Aggregation
# -----------------------
def analyze(repo_path: str, patch_str: str) -> Dict:
    """Analyze only the patch-modified files using all static analyzers."""
    modified_files = get_modified_files(repo_path, patch_str)
    if not modified_files:
        return {"error": "No modified Python files detected."}

    pylint_scores = []
    pylint_issues = {}
    flake8_all = []
    radon_complexities = {}
    radon_mis = []
    mypy_total = 0
    bandit_total = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    total_loc = 0

    for file_path in modified_files:
        # --- Pylint ---
        pylint_result = run_pylint(file_path)
        pylint_scores.append(pylint_result["score"])
        pylint_issues[file_path] = pylint_result["issues"]

        # --- Flake8 ---
        issues = run_flake8(file_path)
        flake8_all.extend(issues)

        # --- Radon (complexity + MI) ---
        radon_complexities[file_path] = run_radon_complexity(file_path)
        radon_mis.append(run_radon_mi(file_path))

        # --- Mypy ---
        mypy_dict= run_mypy(file_path)
        mypy_total += mypy_dict.get("error_count", 0)

        # --- Bandit ---
        bandit_res = run_bandit(file_path)
        for k in bandit_total:
            bandit_total[k] += bandit_res.get(k, 0)

        # --- Count LOC ---
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                total_loc += len(f.readlines())
        except:
            pass

    avg_pylint = sum(pylint_scores) / len(pylint_scores) if pylint_scores else 0.0
    avg_mi = sum(radon_mis) / len(radon_mis) if radon_mis else 0.0

    # --- Compute SQI ---
    sqi_result = compute_sqi(
        pylint_score=avg_pylint,
        radon_mi=avg_mi,
        flake8_issues=flake8_all,
        mypy_errors=mypy_total,
        bandit_counts=bandit_total,
        loc=total_loc,
    )

    return {
        "modified_files": modified_files,
        "sqi": sqi_result,
        "pylint": pylint_issues,
        "flake8": flake8_all,
        "radon": {
            "complexity": radon_complexities,
            "mi_avg": avg_mi
        },
        "mypy": mypy_dict,
        "bandit": bandit_total,
    }


# -----------------------
# Standalone test runner
# -----------------------
if __name__ == "__main__":
    loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True)
    for sample in loader.iter_samples(limit=1):
        patcher = PatchLoader(sample, repos_root="repos_temp")
        patcher.cleanup_old_repos()

        try:
            result = patcher.load_and_apply()
        except Exception as e:
            print(f"❌ Patch application failed: {e}")
            continue

        repo_path = result.get("repo_path")
        diff_text = sample["patch"]

        if not repo_path:
            print("❌ Failed to load repository.")
            break

        print(f"\n📂 Repository cloned and patched at: {repo_path}\n")
        print("🔍 Running code quality analysis...")

        # Inject a test Bandit issue into one of the modified files
        # Bandit analyzer detection test.
        try:
            test_file = None
            for f in os.listdir(os.path.join(repo_path, "astropy", "modeling")):
                if f.endswith("separable.py"):
                    test_file = os.path.join(repo_path, "astropy", "modeling", f)
                    break

            if test_file and os.path.exists(test_file):
                with open(test_file, "a", encoding="utf-8") as f:
                    f.write(
                        "\n\n# === Test Bandit injection ===\n"
                        "import subprocess\n"
                        "subprocess.run('echo vulnerable', shell=True)\n"
                    )
                print(f"💉 Injected Bandit test issue into: {test_file}")
            else:
                print("⚠️ No target file found for Bandit injection.")

        except Exception as e:
            print(f"⚠️ Failed to inject Bandit issue: {e}")

        analysis_results = analyze(repo_path, diff_text)
        print("✅ Analysis complete. Results:")
        print(json.dumps(analysis_results, indent=2))
