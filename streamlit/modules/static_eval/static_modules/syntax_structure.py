# verifier/static_analyzers/syntax_structure.py

"""
Syntax & Structure Analyzer
│
├─ (1) Input parsing
│     → Takes in repo path + diff info (which files and lines changed)
│
├─ (2) Syntax validation
│     → Uses Python’s AST parser (ast.parse)
│     → Detects syntax errors early
│
├─ (3) Structural metrics
│     → Counts number of functions, classes, and AST depth
│     → Average function length in lines
│
├─ (4) Changed function extraction
│     → Finds function names whose line numbers overlap with diff ranges
│
├─ (5) Diff-based structural comparison
│     → Uses diff line ranges to estimate how much the file changed
│     → How much of a file’s structure (functions/classes) was affected by the implemented patch
│     → Produces "ast_diff_ratio"
│
└─ (6) Aggregation
      → Summarizes everything in a single dictionary for reporting
"""

import sys, os
from pathlib import Path

# Dynamically resolve project root (2 levels up from this file)
CURRENT_DIR = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_DIR.parents[2]  # verifier/static_analyzers → verifier → project root
sys.path.append(str(PROJECT_ROOT))

from modules.loading.dataset_loader import DatasetLoader
from modules.loading.patch_loader import PatchLoader
from modules.utils.diff_utils import parse_unified_diff, filter_paths_to_py

# -----------------------------
# (1) Input Parsing
# -----------------------------
def parse_input(repo_path: str, diff_text: str) -> tuple:
    """
    Step 1: Parse inputs to identify changed Python files and line ranges.
    """
    parsed_diff = parse_unified_diff(diff_text)
    changed_files = filter_paths_to_py(list(parsed_diff.keys()))
    return repo_path, {f: parsed_diff[f] for f in changed_files if f in parsed_diff}


# -----------------------------
# (2) AST Helpers
# -----------------------------
def get_ast_depth(node, current=0):
    """
    Recursively compute the maximum nesting depth of an AST node.
    """
    import ast
    if not list(ast.iter_child_nodes(node)):
        return current
    return max(get_ast_depth(child, current + 1) for child in ast.iter_child_nodes(node))


# -----------------------------
# (3) Syntax Validation & Metrics
# -----------------------------
def syntax_ast_validation(file_path: Path) -> dict:
    """
    Step 2 & 3: Validate syntax and extract structural metrics from a Python file.

    Returns:
        dict: {
            "path": str,
            "is_code_valid": bool,
            "n_functions": int,
            "n_classes": int,
            "ast_depth": int,
            "avg_func_length": float,
            "error": str or None
        }
    """
    import ast

    try:
        source = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        is_code_valid = True

        # --- Structural metrics ---
        n_funcs = sum(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
        n_classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        ast_depth = get_ast_depth(tree)

        # Compute average function length in lines
        func_lengths = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                    func_lengths.append(node.end_lineno - node.lineno) # type: ignore 
        avg_func_length = sum(func_lengths) / len(func_lengths) if func_lengths else 0

        return {
            "path": str(file_path),
            "is_code_valid": is_code_valid,
            "n_functions": n_funcs,
            "n_classes": n_classes,
            "ast_depth": ast_depth,
            "avg_func_length": avg_func_length,
            "error": None
        }

    except SyntaxError as e:
        lines = Path(file_path).read_text(encoding="utf-8").splitlines()
        error_line = getattr(e, "lineno", None)

        return {
            "path": str(file_path),
            "is_code_valid": False,
            "error": f"{type(e).__name__} at line {error_line}: {e.msg}",
            "context": lines[error_line - 2:error_line + 1] if error_line and len(lines) > error_line else []
        }
    
# -----------------------------
# (4) Changed Function Extraction
# -----------------------------
def extract_changed_functions(file_path: Path, diff_ranges: list[tuple[int, int]]) -> list[str]:
    """
    Step 4: Identify function names that overlap with the changed line ranges."""
    import ast

    changed_funcs = []
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", start)
            for (diff_start, diff_end) in diff_ranges:
                # Check for line range overlap
                if start and end and not (end < diff_start or start > diff_end):
                    changed_funcs.append(node.name)
                    break
    return changed_funcs

# -----------------------------
# (5) Diff-based Structural Comparison  
# -----------------------------
def compute_ast_diff_ratio(n_functions: int, n_classes: int, changed_functions: list[str]) -> float:
    """
    Step 5: Estimate how much of the file's structure was modified.

    ast_diff_ratio = (# changed functions/classes) / (total functions + classes)
    """
    total_entities = n_functions + n_classes
    if total_entities == 0:
        return 0.0
    ratio = len(changed_functions) / total_entities
    return round(min(ratio, 1.0), 3) # 3 decimal places

# -----------------------------
# (6) Aggregation
# -----------------------------
def analyze_file(repo_path: Path, rel_path: str, diff_ranges: list[tuple[int, int]]) -> dict:
    """
    Step 6: Combine all analysis results into one dictionary per file.
    """
    abs_path = Path(repo_path) / rel_path
    metrics = syntax_ast_validation(abs_path)

    #Add changed functions and AST diff ratio if code is valid
    if metrics["is_code_valid"]:
        changed_funcs = extract_changed_functions(abs_path, diff_ranges)
        metrics["changed_functions"] = changed_funcs
        metrics["ast_diff_ratio"] = compute_ast_diff_ratio(
            metrics["n_functions"],
            metrics["n_classes"],
            changed_funcs
        )

    return metrics


def run_syntax_structure_analysis(repo_path: str, diff_text: str) -> list[dict]:
    """
    Run the full syntax & structure analyzer pipeline on all changed Python files.
    """
    repo_path, parsed_diff = parse_input(repo_path, diff_text)
    report = []

    for rel_path, diff_ranges in parsed_diff.items():
        abs_path = Path(repo_path) / rel_path
        if abs_path.exists():
            file_report = analyze_file(Path(repo_path), rel_path, diff_ranges)
            report.append(file_report)
        else:
            report.append({
                "path": str(abs_path),
                "error": "File not found",
                "is_code_valid": False
            })

    return report


# -----------------------------
# (**) Standalone Test Mode
# -----------------------------
if __name__ == "__main__":
    TEST_SYNTAX_ERROR = False  # Toggle to test invalid syntax

    loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True)
    for sample in loader.iter_samples(limit=1):

        patcher = PatchLoader(
            sample,
            repos_root="./repos_temp"
        )

        patcher.cleanup_old_repos()

        # Clone and apply patch
        try:
            result = patcher.load_and_apply()
        except Exception as e:
            print(f" Patch application failed: {e}")
            continue

        repo_path = result.get("repo_path")
        if not repo_path:
            print(" Failed to load repository.")
            break

        print(f"\n Repository cloned and patched at: {repo_path}\n")

        # -------------------------------------------------------
        # Prepare diff text (must be defined BEFORE file editing)
        # -------------------------------------------------------
        if TEST_SYNTAX_ERROR:
            diff_text = """diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py
index 111111..222222 100644
--- a/astropy/modeling/separable.py
+++ b/astropy/modeling/separable.py
@@ -242,7 +242,7 @@ def _validate_input(x):
-    return np.all(x == 0)
+    return np.all(x == 0  # Missing parenthesis here
"""
            print("Injecting fake syntax error patch for testing")
        else:
            diff_text = sample["patch"]

        # -------------------------------------------------------
        # Physically inject syntax error into the cloned repo
        # -------------------------------------------------------
        if TEST_SYNTAX_ERROR:
            print("Overwriting target file to inject syntax error physically")
            target_rel = "astropy/modeling/separable.py"
            abs_path = Path(repo_path) / target_rel
            if abs_path.exists():
                lines = abs_path.read_text(encoding="utf-8").splitlines(True)
                if len(lines) > 243:
                    lines[243] = "    return np.all(x == 0  # Missing parenthesis here\n"
                    abs_path.write_text("".join(lines), encoding="utf-8")

        # -------------------------------------------------------
        # Run the full static analyzer
        # -------------------------------------------------------
        try:
            report = run_syntax_structure_analysis(repo_path, diff_text)
        except Exception as e:
            print(f" Static analysis failed: {e}")
            continue

        # -------------------------------------------------------
        # Pretty-print the report
        # -------------------------------------------------------
        print("\n Syntax & Structure Analysis Report")
        print("=" * 60)
        for file_report in report:
            print(f"\nFile: {file_report['path']}")
            for k, v in file_report.items():
                if k != "path":
                    print(f"   {k:<20}: {v}")
        print("=" * 60 + "\n")

