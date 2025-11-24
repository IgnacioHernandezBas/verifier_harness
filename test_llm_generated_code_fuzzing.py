#!/usr/bin/env python3
"""
Demo: Fuzzing LLM-Generated Code

Shows how the enhanced fuzzing system handles code created by LLMs
where no existing tests are available to learn from.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer


def demo_llm_generated_new_class():
    """Scenario 1: LLM creates a completely new class"""
    print("="*80)
    print("SCENARIO 1: LLM Creates New Class (No Existing Tests)")
    print("="*80)
    print()

    # Simulated LLM-generated patch
    llm_patch = """
--- a/new_estimator.py
+++ b/new_estimator.py
@@ -0,0 +1,15 @@
+class NewEstimator:
+    \"\"\"A new machine learning estimator created by an LLM\"\"\"
+
+    def __init__(self, alpha: float = 0.5, n_iterations: int = 100,
+                 normalize: bool = True, learning_rate: float = 0.01):
+        self.alpha = alpha
+        self.n_iterations = n_iterations
+        self.normalize = normalize
+        self.learning_rate = learning_rate
+
+    def fit(self, X, y):
+        # Training logic here
+        return self
"""

    patched_code = """
class NewEstimator:
    \"\"\"A new machine learning estimator created by an LLM\"\"\"

    def __init__(self, alpha: float = 0.5, n_iterations: int = 100,
                 normalize: bool = True, learning_rate: float = 0.01):
        self.alpha = alpha
        self.n_iterations = n_iterations
        self.normalize = normalize
        self.learning_rate = learning_rate

    def fit(self, X, y):
        # Training logic here
        return self
"""

    # Analyze patch
    analyzer = PatchAnalyzer()
    patch_analysis = analyzer.parse_patch(llm_patch, patched_code, "new_estimator.py")

    print("Patch Analysis:")
    print(f"  Changed functions: {patch_analysis.changed_functions}")
    print(f"  Changed lines: {len(patch_analysis.all_changed_lines)}")
    print(f"  Class context: {patch_analysis.class_context}")
    print()

    # Generate tests (without repo_path, so pattern learning unavailable)
    # This simulates the case where there are no existing tests
    test_generator = HypothesisTestGenerator(repo_path=Path("/tmp/nonexistent"))
    test_code = test_generator.generate_tests(patch_analysis, patched_code)

    print("Generated Test Code:")
    print("-" * 80)
    print(test_code)
    print("-" * 80)
    print()


def demo_llm_modifies_existing_class():
    """Scenario 2: LLM adds new method to existing class"""
    print("="*80)
    print("SCENARIO 2: LLM Adds New Method to Existing Class")
    print("="*80)
    print()

    llm_patch = """
--- a/sklearn/linear_model/ridge.py
+++ b/sklearn/linear_model/ridge.py
@@ -100,0 +101,10 @@ class RidgeClassifier:
+    def predict_confidence(self, X, threshold: float = 0.5):
+        \"\"\"
+        Predict with confidence scores.
+        New method added by LLM.
+        \"\"\"
+        predictions = self.predict(X)
+        scores = self.decision_function(X)
+        confident = scores > threshold
+        return predictions, confident
"""

    patched_code = """
class RidgeClassifier:
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def predict(self, X):
        return X @ self.coef_

    def decision_function(self, X):
        return X @ self.coef_

    def predict_confidence(self, X, threshold: float = 0.5):
        \"\"\"
        Predict with confidence scores.
        New method added by LLM.
        \"\"\"
        predictions = self.predict(X)
        scores = self.decision_function(X)
        confident = scores > threshold
        return predictions, confident
"""

    analyzer = PatchAnalyzer()
    patch_analysis = analyzer.parse_patch(llm_patch, patched_code, "sklearn/linear_model/ridge.py")

    print("Patch Analysis:")
    print(f"  Changed functions: {patch_analysis.changed_functions}")
    print(f"  Class context: {patch_analysis.class_context}")
    print()

    # Generate tests - would try to learn RidgeClassifier instantiation patterns
    # but fall back to signature extraction for the new method
    test_generator = HypothesisTestGenerator(repo_path=Path("/tmp/nonexistent"))
    test_code = test_generator.generate_tests(patch_analysis, patched_code)

    print("Generated Test Code:")
    print("-" * 80)
    print(test_code)
    print("-" * 80)
    print()


def demo_llm_new_standalone_function():
    """Scenario 3: LLM creates a new standalone function"""
    print("="*80)
    print("SCENARIO 3: LLM Creates New Standalone Function")
    print("="*80)
    print()

    llm_patch = """
--- a/utils.py
+++ b/utils.py
@@ -50,0 +51,8 @@
+def calculate_metric(data: list, threshold: float = 0.5,
+                    normalize: bool = True) -> float:
+    \"\"\"Calculate a custom metric. Created by LLM.\"\"\"
+    values = [x for x in data if x > threshold]
+    if normalize and values:
+        return sum(values) / len(values)
+    return sum(values) if values else 0.0
"""

    patched_code = """
def existing_function():
    pass

def calculate_metric(data: list, threshold: float = 0.5,
                    normalize: bool = True) -> float:
    \"\"\"Calculate a custom metric. Created by LLM.\"\"\"
    values = [x for x in data if x > threshold]
    if normalize and values:
        return sum(values) / len(values)
    return sum(values) if values else 0.0
"""

    analyzer = PatchAnalyzer()
    patch_analysis = analyzer.parse_patch(llm_patch, patched_code, "utils.py")

    print("Patch Analysis:")
    print(f"  Changed functions: {patch_analysis.changed_functions}")
    print(f"  Standalone function (no class context)")
    print()

    # Generate tests - standalone functions already work well
    test_generator = HypothesisTestGenerator()
    test_code = test_generator.generate_tests(patch_analysis, patched_code)

    print("Generated Test Code:")
    print("-" * 80)
    print(test_code)
    print("-" * 80)
    print()


def main():
    print()
    print("╔" + "="*78 + "╗")
    print("║" + " " * 15 + "FUZZING LLM-GENERATED CODE DEMO" + " " * 31 + "║")
    print("╚" + "="*78 + "╝")
    print()

    print("This demo shows how the enhanced fuzzing system handles code generated")
    print("by LLMs where no existing tests are available to learn from.")
    print()

    print("Three-Tier Fallback Strategy:")
    print("  1. Learn from existing tests (best)")
    print("  2. Extract from function signature (good - NEW!)")
    print("  3. Existence check (fallback)")
    print()

    # Run scenarios
    demo_llm_generated_new_class()
    demo_llm_modifies_existing_class()
    demo_llm_new_standalone_function()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print("✅ Signature-based extraction implemented!")
    print()
    print("For LLM-generated code:")
    print("  • Extracts type hints (alpha: float → st.floats(...))")
    print("  • Uses default values (alpha=0.5 → tests around 0.5)")
    print("  • Applies heuristics (threshold → st.floats(0.0, 1.0))")
    print("  • Falls back to mixed strategies if needed")
    print()
    print("Result:")
    print("  • NEW code gets intelligent tests (not just existence checks)")
    print("  • Tests actually execute the LLM-generated code")
    print("  • Coverage significantly better than before")
    print()
    print("="*80)


if __name__ == "__main__":
    main()
