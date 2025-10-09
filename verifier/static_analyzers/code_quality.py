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
│     → Cyclomatic complexity per function
│
├─ (5) Diff-based structural comparison
│     → Uses diff line ranges to estimate how much the file changed
│     → How much of a file’s structure (functions/classes) was affected by the implemented patch
│     → Produces "ast_diff_ratio"
│
└─ (6) Aggregation
      → Summarizes everything in a single dictionary for reporting
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
from verifier.patch_loader import PatchLoader
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
    This avoids parsing stderr/stdout and works for Pylint ≥3.0.
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
    """Run flake8 on a single file and return list of style issues."""
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
# -----------------------
def run_radon(file_path: str) -> List[Dict]:
    """Run Radon cyclomatic complexity analysis."""
    try:
        result = subprocess.run(
            ["radon", "cc", "-s", "-j", file_path],
            capture_output=True,
            text=True,
            check=False,
        )
        cc_data = json.loads(result.stdout or "{}")
        complexities = []
        for func in cc_data.get(file_path, []):
            complexities.append({
                "name": func.get("name"),
                "complexity": func.get("complexity"),
                "lineno": func.get("lineno"),
            })
        return complexities
    except Exception as e:
        print(f"Radon failed for {file_path}: {e}")
        return []


# -----------------------
# (5) Diff-based structural comparison (placeholder)
# -----------------------
# This is a placeholder. A full implementation would require AST diffing libraries.


# -----------------------
# (6) Aggregation
# -----------------------
def analyze(repo_path: str, patch_str: str) -> Dict:
    """Analyze only the patch-modified files using diff_utils."""
    modified_files = get_modified_files(repo_path, patch_str)
    if not modified_files:
        return {"error": "No modified Python files detected."}

    pylint_scores = []
    pylint_issues = {}
    flake8_issues = {}
    radon_complexities = {}

    for file_path in modified_files:
        # --- Pylint ---
        pylint_result = run_pylint(file_path)
        pylint_scores.append(pylint_result["score"])
        pylint_issues[file_path] = pylint_result["issues"]

        # --- Flake8 ---
        flake8_issues[file_path] = run_flake8(file_path)

        # --- Radon ---
        radon_complexities[file_path] = run_radon(file_path)

    avg_pylint = sum(pylint_scores) / len(pylint_scores) if pylint_scores else 0.0

    return {
        "modified_files": modified_files,
        "pylint_avg_score": round(avg_pylint, 2),
        "pylint": pylint_issues,
        "flake8": flake8_issues,
        "radon": radon_complexities,
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
        analysis_results = analyze(repo_path, diff_text)
        print("✅ Analysis complete. Results:")
        print(json.dumps(analysis_results, indent=2))
