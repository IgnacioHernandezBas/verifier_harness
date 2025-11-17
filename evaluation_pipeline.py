"""
Integrated Evaluation Pipeline: Static + Dynamic Fuzzing

This module combines:
1. Static verification (existing code quality analyzers)
2. Dynamic fuzzing (new change-aware fuzzing)

to provide comprehensive patch evaluation for SWE-bench tasks.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
from verifier.dynamic_analyzers.singularity_executor import SingularityTestExecutor
from verifier.dynamic_analyzers.coverage_analyzer import CoverageAnalyzer
# Import static analyzers from streamlit modules
import streamlit.modules.static_eval.static_modules.code_quality as code_quality
import streamlit.modules.static_eval.static_modules.syntax_structure as syntax_structure


class EvaluationPipeline:
    """
    Complete evaluation pipeline: static verification + dynamic fuzzing.

    This pipeline implements change-aware fuzzing:
    - Analyzes patches to find what changed
    - Generates targeted tests for changed code
    - Executes tests in Singularity containers
    - Measures coverage only for changed lines
    """

    def __init__(
        self,
        singularity_image_path: str = "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif",
        enable_static: bool = True,
        enable_fuzzing: bool = True,
        fuzzing_timeout: int = 120,
        static_threshold: float = 0.5,
        coverage_threshold: float = 0.5,
    ):
        """
        Initialize the evaluation pipeline.

        Args:
            singularity_image_path: Path to Singularity .sif image
            enable_static: Enable static verification
            enable_fuzzing: Enable dynamic fuzzing
            fuzzing_timeout: Timeout for fuzzing tests (seconds)
            static_threshold: Minimum static quality score (0-1)
            coverage_threshold: Minimum coverage for changed lines (0-1)
        """
        # Static analysis components
        self.enable_static = enable_static
        # Static analyzers are now functional modules from streamlit section
        self.code_quality_module = code_quality
        self.syntax_structure_module = syntax_structure

        # Dynamic fuzzing components
        self.enable_fuzzing = enable_fuzzing
        if enable_fuzzing:
            self.patch_analyzer = PatchAnalyzer()
            self.test_generator = HypothesisTestGenerator()
            self.test_executor = SingularityTestExecutor(
                image_path=singularity_image_path,
                timeout=fuzzing_timeout
            )
            self.coverage_analyzer = CoverageAnalyzer()

        # Thresholds
        self.static_threshold = static_threshold
        self.coverage_threshold = coverage_threshold

    def evaluate_patch(
        self,
        patch_data: Dict[str, Any],
        skip_static: bool = False,
        skip_fuzzing: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate a patch using static + dynamic analysis.

        Args:
            patch_data: {
                'id': str (e.g., 'django__django-12345'),
                'diff': str (unified diff),
                'patched_code': str (full code after patch),
                'original_code': str (optional, for comparison),
                'repo_path': Path (optional, for testing in repo context)
            }
            skip_static: Skip static verification
            skip_fuzzing: Skip dynamic fuzzing

        Returns:
            {
                'patch_id': str,
                'verdict': 'ACCEPT' | 'REJECT' | 'WARNING' | 'ERROR',
                'reason': str,
                'static_result': dict (if enabled),
                'fuzzing_result': dict (if enabled),
                'timestamp': float,
                'execution_time': float
            }
        """
        start_time = time.time()
        patch_id = patch_data.get('id', 'unknown')

        result = {
            'patch_id': patch_id,
            'verdict': 'UNKNOWN',
            'reason': '',
            'timestamp': start_time
        }

        print(f"\n{'='*80}")
        print(f"Evaluating Patch: {patch_id}")
        print(f"{'='*80}")

        # ===================================================================
        # PHASE 1: Static Verification
        # ===================================================================
        if self.enable_static and not skip_static:
            print(f"\n[PHASE 1] Static Verification...")
            static_result = self._run_static_verification(patch_data)
            result['static_result'] = static_result

            # Check static quality gate
            sqi_score = static_result.get('sqi_score', 0.0)
            print(f"  Static Quality Index (SQI): {sqi_score:.2f}")

            if sqi_score < self.static_threshold:
                result['verdict'] = 'REJECT'
                result['reason'] = f'Poor static quality (SQI={sqi_score:.2f} < {self.static_threshold})'
                result['execution_time'] = time.time() - start_time
                return result

            print(f"  ✓ Static verification passed")

        # ===================================================================
        # PHASE 2: Dynamic Fuzzing
        # ===================================================================
        if self.enable_fuzzing and not skip_fuzzing:
            print(f"\n[PHASE 2] Dynamic Change-Aware Fuzzing...")

            try:
                fuzzing_result = self._run_dynamic_fuzzing(patch_data)
                result['fuzzing_result'] = fuzzing_result

                # Check fuzzing results
                if fuzzing_result.get('status') == 'error':
                    result['verdict'] = 'WARNING'
                    result['reason'] = f"Fuzzing error: {fuzzing_result.get('error', 'unknown')}"
                elif not fuzzing_result.get('tests_passed', False):
                    result['verdict'] = 'REJECT'
                    result['reason'] = 'Generated fuzzing tests failed'
                elif fuzzing_result.get('coverage', {}).get('overall_coverage', 0) < self.coverage_threshold:
                    cov = fuzzing_result['coverage']['overall_coverage']
                    result['verdict'] = 'WARNING'
                    result['reason'] = f'Low coverage of changed lines ({cov:.1%} < {self.coverage_threshold:.1%})'
                else:
                    result['verdict'] = 'ACCEPT'
                    cov = fuzzing_result['coverage']['overall_coverage']
                    result['reason'] = f'Passed all checks (coverage: {cov:.1%})'

            except Exception as e:
                print(f"  ✗ Fuzzing error: {e}")
                result['verdict'] = 'ERROR'
                result['reason'] = f'Fuzzing exception: {str(e)}'
                result['fuzzing_result'] = {'status': 'error', 'error': str(e)}

        # ===================================================================
        # FINAL VERDICT
        # ===================================================================
        if result['verdict'] == 'UNKNOWN':
            if not self.enable_static and not self.enable_fuzzing:
                result['verdict'] = 'ERROR'
                result['reason'] = 'No analysis enabled'
            else:
                result['verdict'] = 'ACCEPT'
                result['reason'] = 'Passed available checks'

        result['execution_time'] = time.time() - start_time

        print(f"\n{'='*80}")
        print(f"VERDICT: {result['verdict']}")
        print(f"REASON: {result['reason']}")
        print(f"TIME: {result['execution_time']:.2f}s")
        print(f"{'='*80}\n")

        return result

    def _run_static_verification(self, patch_data: Dict) -> Dict:
        """Run static code quality analysis using streamlit modules"""
        diff = patch_data.get('diff', '')
        repo_path = patch_data.get('repo_path')

        if not repo_path:
            return {
                'sqi_score': 0.0,
                'error': 'No repository path provided for static analysis'
            }

        # Default configuration for all tools
        config = {
            'checks': {
                'pylint': True,
                'flake8': True,
                'radon': True,
                'mypy': True,
                'bandit': True,
            },
            'weights': {
                'pylint': 0.5,
                'flake8': 0.15,
                'radon': 0.25,
                'mypy': 0.05,
                'bandit': 0.05,
            }
        }

        try:
            # Run code quality analysis
            cq_results = self.code_quality_module.analyze(
                repo_path=str(repo_path),
                patch_str=diff,
                config=config
            )

            # Run syntax & structure analysis
            ss_results = self.syntax_structure_module.run_syntax_structure_analysis(
                repo_path=str(repo_path),
                diff_text=diff
            )

            # Extract SQI score (normalized to 0-1 from 0-100)
            sqi_score = cq_results.get('sqi', {}).get('SQI', 0.0) / 100.0

            return {
                'sqi_score': sqi_score,
                'sqi_classification': cq_results.get('sqi', {}).get('classification', 'Unknown'),
                'code_quality': cq_results,
                'syntax_structure': ss_results,
            }
        except Exception as e:
            print(f"  ✗ Static analysis error: {e}")
            return {
                'sqi_score': 0.0,
                'error': str(e)
            }

    def _calculate_sqi(self, quality_result: Dict, syntax_result: Dict) -> float:
        """
        Calculate Static Quality Index from analyzer results.

        Returns a score from 0.0 to 1.0.
        """
        # Simple weighted combination
        # Adjust weights based on your priorities
        weights = {
            'has_syntax_errors': -0.5,  # Major penalty
            'complexity': 0.2,
            'maintainability': 0.3,
            'documentation': 0.0,  # Don't penalize for missing docs in patches
        }

        score = 1.0

        # Syntax errors are critical
        if syntax_result.get('has_errors', False):
            score -= 0.5

        # Complexity (lower is better, normalized)
        complexity = quality_result.get('complexity', {}).get('average_complexity', 5)
        if complexity > 10:
            score -= 0.2
        elif complexity > 15:
            score -= 0.3

        # Ensure score is in [0, 1]
        return max(0.0, min(1.0, score))

    def _run_dynamic_fuzzing(self, patch_data: Dict) -> Dict:
        """Run dynamic fuzzing with change-aware coverage"""
        diff = patch_data.get('diff', '')
        patched_code = patch_data.get('patched_code', '')
        repo_path = patch_data.get('repo_path')

        # Step 1: Analyze patch to find changes
        print(f"  Step 1: Analyzing patch...")
        patch_analysis = self.patch_analyzer.parse_patch(diff, patched_code)

        if not patch_analysis.changed_functions:
            print(f"  ℹ No functions changed - skipping fuzzing")
            return {
                'status': 'skipped',
                'reason': 'No functions changed',
                'tests_passed': True,
                'coverage': {
                    'overall_coverage': 1.0,
                    'total_changed_lines': 0
                }
            }

        print(f"  Changed functions: {patch_analysis.changed_functions}")
        print(f"  Changed lines: {len(patch_analysis.all_changed_lines)}")

        # Step 2: Generate tests
        print(f"  Step 2: Generating fuzzing tests...")
        test_code = self.test_generator.generate_tests(patch_analysis, patched_code)
        test_count = test_code.count('def test_')
        print(f"  Generated {test_count} test functions")

        # Step 3: Execute tests in Singularity
        print(f"  Step 3: Executing tests in Singularity container...")
        if repo_path:
            success, output, coverage_data = self.test_executor.run_tests_with_existing_infrastructure(
                repo_path=Path(repo_path),
                test_code=test_code
            )
        else:
            success, output, coverage_data = self.test_executor.run_tests_in_container(
                test_code=test_code,
                source_code=patched_code
            )

        # Step 4: Analyze coverage (change-aware)
        print(f"  Step 4: Analyzing coverage (change-aware)...")
        coverage_result = self.coverage_analyzer.calculate_changed_line_coverage(
            coverage_data,
            patch_analysis.changed_lines,
            patch_analysis.all_changed_lines
        )

        print(f"  Coverage of changed lines: {coverage_result['overall_coverage']:.1%}")
        print(f"  Covered: {coverage_result['total_covered_lines']}/{coverage_result['total_changed_lines']} lines")

        return {
            'status': 'completed',
            'tests_generated': test_count,
            'tests_passed': success,
            'test_output': output[:1000],  # Truncate for brevity
            'coverage': coverage_result,
            'changed_functions': patch_analysis.changed_functions,
            'change_types': patch_analysis.change_types
        }

    def evaluate_batch(
        self,
        patches: List[Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple patches in batch.

        Args:
            patches: List of patch_data dicts
            output_file: Optional file to save results (JSON)

        Returns:
            List of evaluation results
        """
        results = []

        for i, patch_data in enumerate(patches, 1):
            print(f"\n{'#'*80}")
            print(f"# Patch {i}/{len(patches)}")
            print(f"{'#'*80}")

            result = self.evaluate_patch(patch_data)
            results.append(result)

        # Save results if output file specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open('w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✓ Results saved to: {output_file}")

        # Print summary
        self._print_batch_summary(results)

        return results

    def _print_batch_summary(self, results: List[Dict]):
        """Print summary statistics for batch evaluation"""
        total = len(results)
        accept = sum(1 for r in results if r['verdict'] == 'ACCEPT')
        reject = sum(1 for r in results if r['verdict'] == 'REJECT')
        warning = sum(1 for r in results if r['verdict'] == 'WARNING')
        error = sum(1 for r in results if r['verdict'] == 'ERROR')

        avg_time = sum(r.get('execution_time', 0) for r in results) / total if total > 0 else 0

        print(f"\n{'='*80}")
        print(f"BATCH EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Patches: {total}")
        print(f"  ✓ ACCEPT:  {accept} ({accept/total*100:.1f}%)")
        print(f"  ✗ REJECT:  {reject} ({reject/total*100:.1f}%)")
        print(f"  ⚠ WARNING: {warning} ({warning/total*100:.1f}%)")
        print(f"  ⚠ ERROR:   {error} ({error/total*100:.1f}%)")
        print(f"Avg Time: {avg_time:.2f}s/patch")
        print(f"{'='*80}\n")


# Example usage
if __name__ == "__main__":
    # Example patch data
    patch = {
        'id': 'example-001',
        'diff': """
--- a/example.py
+++ b/example.py
@@ -10,6 +10,8 @@ def divide(a, b):
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b
""",
        'patched_code': """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def multiply(a, b):
    return a * b
"""
    }

    # Initialize pipeline
    pipeline = EvaluationPipeline(
        enable_static=True,
        enable_fuzzing=True,
        static_threshold=0.5,
        coverage_threshold=0.5
    )

    # Evaluate
    result = pipeline.evaluate_patch(patch)

    print(f"\nFinal result:")
    print(json.dumps(result, indent=2))
