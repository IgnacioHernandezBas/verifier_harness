#!/usr/bin/env python3
"""
Integrated Verification Script

This script demonstrates how to run the full verification pipeline including:
1. Static Analysis (pylint, flake8, mypy, bandit)
2. Dynamic Analysis - SWE-bench tests (via Podman containers)
3. Fuzzing (Hypothesis-based property testing)
4. Invariance Testing (property-based tests)

Usage:
    python run_integrated_verification.py --instance django__django-12345
    python run_integrated_verification.py --experiment 20250911_isea_claude-3.5-sonnet-20241022 --limit 10
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from verifier.dynamic_analyzers.swebench_singularity_executor import (
    SingularitySWEBenchExecutor,
    TestType
)
from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator


class IntegratedVerifier:
    """
    Complete verification pipeline combining all analysis types.
    """

    def __init__(
        self,
        experiment_name: str,
        experiments_base: str = "/fs/nexus-scratch/ihbas/generated_patches/experiments/evaluation/lite",
        scratch_dir: str = "/scratch0/ihbas",
        enable_static: bool = True,
        enable_swebench: bool = True,
        enable_fuzzing: bool = True,
        enable_invariance: bool = True,
        timeout: int = 300
    ):
        """
        Initialize the integrated verifier.

        Args:
            experiment_name: Name of the SWE-bench experiment
            experiments_base: Base path to experiments
            scratch_dir: Local scratch for Podman (must be on compute node)
            enable_static: Run static analysis
            enable_swebench: Run SWE-bench official tests
            enable_fuzzing: Run fuzzing tests
            enable_invariance: Run invariance tests
            timeout: Test timeout in seconds
        """
        self.experiment_name = experiment_name
        self.experiment_dir = Path(experiments_base) / experiment_name / "logs"
        self.scratch_dir = Path(scratch_dir)

        self.enable_static = enable_static
        self.enable_swebench = enable_swebench
        self.enable_fuzzing = enable_fuzzing
        self.enable_invariance = enable_invariance

        # Initialize components
        if enable_swebench or enable_fuzzing or enable_invariance:
            self.singularity_executor = SingularitySWEBenchExecutor(
                scratch_dir=scratch_dir,
                timeout=timeout
            )

        if enable_fuzzing:
            self.patch_analyzer = PatchAnalyzer()
            self.test_generator = HypothesisTestGenerator(enable_differential=True)

    def get_instances(self, limit: Optional[int] = None) -> List[str]:
        """Get list of instance IDs from experiment directory."""
        instances = []
        for instance_dir in sorted(self.experiment_dir.iterdir()):
            if instance_dir.is_dir():
                instances.append(instance_dir.name)
        if limit:
            instances = instances[:limit]
        return instances

    def load_patch(self, instance_id: str) -> Dict[str, Any]:
        """Load patch data for an instance."""
        instance_dir = self.experiment_dir / instance_id

        patch_data = {
            'instance_id': instance_id,
            'diff': '',
            'eval_script': None
        }

        # Load patch diff
        patch_file = instance_dir / "patch.diff"
        if patch_file.exists():
            patch_data['diff'] = patch_file.read_text()

        # Load eval script path
        eval_script = instance_dir / "eval.sh"
        if eval_script.exists():
            patch_data['eval_script'] = eval_script

        return patch_data

    def generate_fuzzing_tests(self, patch_data: Dict) -> Optional[str]:
        """Generate fuzzing tests for a patch."""
        if not self.enable_fuzzing:
            return None

        diff = patch_data.get('diff', '')
        if not diff:
            return None

        try:
            # Analyze patch
            patch_analysis = self.patch_analyzer.parse_patch(diff, "")

            if not patch_analysis.changed_functions:
                return None

            # Generate tests
            test_code = self.test_generator.generate_tests(
                patch_analysis,
                patched_code="",
                original_code=None
            )
            return test_code
        except Exception as e:
            print(f"  Warning: Could not generate fuzzing tests: {e}")
            return None

    def generate_invariance_tests(self, patch_data: Dict) -> Optional[str]:
        """Generate invariance/property-based tests for a patch."""
        if not self.enable_invariance:
            return None

        # Example invariance test template
        # In practice, you'd generate these based on the patch content
        invariance_test_template = '''
import pytest
from hypothesis import given, strategies as st, settings

# Invariance tests for the patched code
# These test properties that should hold regardless of input

@settings(max_examples=50, deadline=None)
class TestInvariance:
    """Property-based invariance tests."""

    @given(st.integers())
    def test_integer_property(self, x):
        """Example: Test that some integer property holds."""
        # Replace with actual invariance tests
        assert isinstance(x, int)

    @given(st.text(max_size=100))
    def test_string_property(self, s):
        """Example: Test that some string property holds."""
        # Replace with actual invariance tests
        assert isinstance(s, str)
'''
        return invariance_test_template

    def verify_instance(self, instance_id: str) -> Dict[str, Any]:
        """
        Run complete verification on a single instance.

        Returns dict with results from all enabled verification phases.
        """
        print(f"\n{'='*70}")
        print(f"Verifying: {instance_id}")
        print(f"{'='*70}")

        result = {
            'instance_id': instance_id,
            'static': None,
            'swebench': None,
            'fuzzing': None,
            'invariance': None,
            'overall_verdict': 'UNKNOWN',
            'errors': []
        }

        # Load patch data
        patch_data = self.load_patch(instance_id)

        if not patch_data['diff']:
            result['errors'].append("No patch.diff found")
            result['overall_verdict'] = 'ERROR'
            return result

        # =====================================================================
        # PHASE 1: Static Analysis
        # =====================================================================
        if self.enable_static:
            print("\n[Phase 1] Static Analysis...")
            # TODO: Integrate with existing static analyzers
            # For now, skip static analysis
            print("  (Skipped - not implemented in this example)")

        # =====================================================================
        # PHASE 2: SWE-bench Official Tests
        # =====================================================================
        if self.enable_swebench and patch_data['eval_script']:
            print("\n[Phase 2] SWE-bench Tests...")
            try:
                swebench_result = self.singularity_executor.run_swebench_tests(
                    instance_id=instance_id,
                    patch_diff=patch_data['diff'],
                    eval_script_path=patch_data['eval_script']
                )
                result['swebench'] = swebench_result.to_dict()

                if swebench_result.success:
                    print(f"  ✓ PASS (exit code: {swebench_result.exit_code})")
                else:
                    print(f"  ✗ FAIL (exit code: {swebench_result.exit_code})")
                    if swebench_result.error:
                        print(f"    Error: {swebench_result.error}")

            except Exception as e:
                result['errors'].append(f"SWE-bench error: {str(e)}")
                print(f"  ✗ ERROR: {e}")

        # =====================================================================
        # PHASE 3: Fuzzing Tests
        # =====================================================================
        if self.enable_fuzzing:
            print("\n[Phase 3] Fuzzing Tests...")
            fuzzing_tests = self.generate_fuzzing_tests(patch_data)

            if fuzzing_tests:
                try:
                    fuzzing_result = self.singularity_executor.run_custom_tests(
                        instance_id=instance_id,
                        patch_diff=patch_data['diff'],
                        test_code=fuzzing_tests,
                        test_type=TestType.FUZZING
                    )
                    result['fuzzing'] = fuzzing_result.to_dict()

                    if fuzzing_result.success:
                        print(f"  ✓ PASS")
                    else:
                        print(f"  ✗ FAIL")
                        if fuzzing_result.error:
                            print(f"    Error: {fuzzing_result.error}")

                except Exception as e:
                    result['errors'].append(f"Fuzzing error: {str(e)}")
                    print(f"  ✗ ERROR: {e}")
            else:
                print("  (Skipped - no changed functions)")

        # =====================================================================
        # PHASE 4: Invariance Tests
        # =====================================================================
        if self.enable_invariance:
            print("\n[Phase 4] Invariance Tests...")
            invariance_tests = self.generate_invariance_tests(patch_data)

            if invariance_tests:
                try:
                    invariance_result = self.singularity_executor.run_custom_tests(
                        instance_id=instance_id,
                        patch_diff=patch_data['diff'],
                        test_code=invariance_tests,
                        test_type=TestType.INVARIANCE
                    )
                    result['invariance'] = invariance_result.to_dict()

                    if invariance_result.success:
                        print(f"  ✓ PASS")
                    else:
                        print(f"  ✗ FAIL")

                except Exception as e:
                    result['errors'].append(f"Invariance error: {str(e)}")
                    print(f"  ✗ ERROR: {e}")

        # =====================================================================
        # Compute Overall Verdict
        # =====================================================================
        result['overall_verdict'] = self._compute_verdict(result)

        print(f"\n{'='*70}")
        print(f"VERDICT: {result['overall_verdict']}")
        print(f"{'='*70}")

        return result

    def _compute_verdict(self, result: Dict) -> str:
        """Compute overall verdict from all test results."""
        # Check for errors
        if result['errors']:
            return 'ERROR'

        # SWE-bench is primary
        if result['swebench']:
            if not result['swebench'].get('success', False):
                return 'FAIL_SWEBENCH'

        # Check fuzzing
        if result['fuzzing']:
            if not result['fuzzing'].get('success', False):
                return 'FAIL_FUZZING'

        # Check invariance
        if result['invariance']:
            if not result['invariance'].get('success', False):
                return 'FAIL_INVARIANCE'

        # All passed
        if result['swebench'] and result['swebench'].get('success', False):
            return 'PASS'

        return 'UNKNOWN'

    def verify_batch(
        self,
        instances: Optional[List[str]] = None,
        limit: Optional[int] = None,
        output_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Verify multiple instances.

        Args:
            instances: List of instance IDs (or None to use all)
            limit: Max number of instances to process
            output_file: Path to save results JSON

        Returns:
            List of verification results
        """
        if instances is None:
            instances = self.get_instances(limit=limit)

        results = []
        for i, instance_id in enumerate(instances, 1):
            print(f"\n{'#'*70}")
            print(f"# Instance {i}/{len(instances)}")
            print(f"{'#'*70}")

            result = self.verify_instance(instance_id)
            results.append(result)

        # Print summary
        self._print_summary(results)

        # Save results
        if output_file:
            Path(output_file).write_text(json.dumps(results, indent=2))
            print(f"\nResults saved to: {output_file}")

        return results

    def _print_summary(self, results: List[Dict]):
        """Print summary of batch verification."""
        total = len(results)
        verdicts = {}
        for r in results:
            v = r['overall_verdict']
            verdicts[v] = verdicts.get(v, 0) + 1

        print(f"\n{'='*70}")
        print("VERIFICATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total: {total}")
        for verdict, count in sorted(verdicts.items()):
            pct = count / total * 100
            print(f"  {verdict}: {count} ({pct:.1f}%)")
        print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="Run integrated verification on SWE-bench patches"
    )
    parser.add_argument(
        "--experiment",
        default="20250911_isea_claude-3.5-sonnet-20241022",
        help="Experiment name"
    )
    parser.add_argument(
        "--instance",
        help="Single instance ID to verify"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Max number of instances to verify"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--no-static",
        action="store_true",
        help="Disable static analysis"
    )
    parser.add_argument(
        "--no-swebench",
        action="store_true",
        help="Disable SWE-bench tests"
    )
    parser.add_argument(
        "--no-fuzzing",
        action="store_true",
        help="Disable fuzzing tests"
    )
    parser.add_argument(
        "--no-invariance",
        action="store_true",
        help="Disable invariance tests"
    )

    args = parser.parse_args()

    # Initialize verifier
    verifier = IntegratedVerifier(
        experiment_name=args.experiment,
        enable_static=not args.no_static,
        enable_swebench=not args.no_swebench,
        enable_fuzzing=not args.no_fuzzing,
        enable_invariance=not args.no_invariance
    )

    # Run verification
    if args.instance:
        result = verifier.verify_instance(args.instance)
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))
    else:
        verifier.verify_batch(limit=args.limit, output_file=args.output)


if __name__ == "__main__":
    main()
