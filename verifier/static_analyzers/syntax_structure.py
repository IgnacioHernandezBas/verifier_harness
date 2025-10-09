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
│
├─ (4) Diff-based structural comparison
│     → Uses diff line ranges to estimate how much the file changed
│     → Produces "ast_diff_ratio"
│
├─ (5) Changed function extraction
│     → Finds function names whose line numbers overlap with diff ranges
│
└─ (6) Aggregation
      → Summarizes everything in a single dictionary for reporting
"""

import sys, os
from pathlib import Path

sys.path.append(os.path.abspath("C:/Users/Usuario/OneDrive/Escritorio/verifier_harness"))

from swebench_integration.dataset_loader import DatasetLoader
from verifier.patch_loader import PatchLoader
from verifier.utils.diff_utils import parse_unified_diff, filter_paths_to_py


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
        return {
            "path": str(file_path),
            "is_code_valid": False,
            "n_functions": 0,
            "n_classes": 0,
            "ast_depth": 0,
            "avg_func_length": 0,
            "error": str(e)
        }


# -----------------------------
# (**) Standalone Test Mode
# -----------------------------
if __name__ == "__main__":
    # Set to True to inject a fake syntax error patch for testing
    TEST_SYNTAX_ERROR = True

    loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True)
    for sample in loader.iter_samples(limit=1):

        patcher = PatchLoader(
            sample,
            repos_root="C:/Users/Usuario/OneDrive/Escritorio/verifier_harness/repos_temp"
        )

        # Clean old repos before cloning
        patcher.cleanup_old_repos()

        # Clone and apply the SWE-bench patch
        try:
            result = patcher.load_and_apply()
        except Exception as e:
            print(f"Patch application failed: {e}")
            continue

        repo_path = result.get("repo_path")
        if not repo_path:
            print("Failed to load repository.")
            break

        print(f"Repository cloned and patched at: {repo_path}")

        # Inject fake patch if testing syntax error
        if TEST_SYNTAX_ERROR:
            fake_patch = """diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py
index 111111..222222 100644
--- a/astropy/modeling/separable.py
+++ b/astropy/modeling/separable.py
@@ -242,7 +242,7 @@ def _validate_input(x):
-    return np.all(x == 0)
+    return np.all(x == 0  # Missing parenthesis here
"""
            diff_text = fake_patch
            print("Injecting fake syntax error patch for testing")
        else:
            diff_text = sample["patch"]

        # Parse diff and run analyzer
        repo_path, parsed_diff = parse_input(repo_path, diff_text)
        print("Parsed diff:", parsed_diff)

        for rel_path in parsed_diff.keys():
          abs_path = Path(repo_path) / rel_path
          if abs_path.exists():
              print(f"Analyzing {abs_path}")

              if TEST_SYNTAX_ERROR:
                  # Inject a syntax error directly into the file
                  with open(abs_path, "r+", encoding="utf-8") as f:
                      lines = f.readlines()
                      # Example: break line 243 intentionally
                      if len(lines) > 243:
                          lines[243] = "    return np.all(x == 0  # Missing parenthesis here\n"
                      f.seek(0)
                      f.writelines(lines)
                      f.truncate()

              metrics = syntax_ast_validation(abs_path)
              print(metrics)
          else:
              print(f"File not found: {abs_path}")

