#!/usr/bin/env python3
"""
SLURM worker script for integrated pipeline.
Processes a single SWE-bench instance.
"""

import sys
import json
import argparse
from pathlib import Path
import time
import traceback
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from swebench_integration import DatasetLoader, PatchLoader
from swebench_singularity import Config, SingularityBuilder, DockerImageResolver
from verifier.dynamic_analyzers.patch_analyzer import PatchAnalyzer
from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
from verifier.dynamic_analyzers.coverage_analyzer import CoverageAnalyzer
from verifier.dynamic_analyzers.analyze_coverage_unified import analyze_coverage_unified
from verifier.dynamic_analyzers import test_patch_singularity
from verifier.utils.diff_utils import parse_unified_diff, filter_paths_to_py
from verifier.rules import RULE_IDS

import streamlit.modules.static_eval.static_modules.code_quality as code_quality
import streamlit.modules.static_eval.static_modules.syntax_structure as syntax_structure


class IntegratedPipelineWorker:
    """Worker for running integrated pipeline on a single instance."""

    def __init__(self, config: dict):
        """Initialize worker with configuration."""
        self.config = config

        # Set Docker credentials for Singularity
        os.environ["APPTAINER_DOCKER_USERNAME"] = "nacheitor12"
        os.environ["APPTAINER_DOCKER_PASSWORD"] = "wN/^4Me%,!5zz_q"
        os.environ["SINGULARITY_DOCKER_USERNAME"] = "nacheitor12"
        os.environ["SINGULARITY_DOCKER_PASSWORD"] = "wN/^4Me%,!5zz_q"

        # Initialize Singularity components
        self.swebench_config = Config()
        self.swebench_config.set("singularity.cache_dir", "/fs/nexus-scratch/ihbas/.cache/swebench_singularity")
        self.swebench_config.set("singularity.tmp_dir", "/fs/nexus-scratch/ihbas/.tmp/singularity_build")
        self.swebench_config.set("singularity.cache_internal_dir", "/fs/nexus-scratch/ihbas/.singularity/cache")
        self.swebench_config.set("singularity.build_timeout", 1800)
        self.swebench_config.set("docker.max_retries", 3)
        self.swebench_config.set("docker.image_patterns", [
            "swebench/sweb.eval.x86_64.{repo}_1776_{repo}-{version}:latest",
        ])

        self.builder = SingularityBuilder(self.swebench_config)
        self.resolver = DockerImageResolver(self.swebench_config)

    def run(self, instance_id: str) -> dict:
        """
        Run integrated pipeline on a single instance.

        Args:
            instance_id: SWE-bench instance ID

        Returns:
            Results dictionary
        """
        start_time = time.time()

        try:
            print(f"Loading instance: {instance_id}")

            # Load sample from dataset
            loader = DatasetLoader("princeton-nlp/SWE-bench_Verified", hf_mode=True, split="test")
            sample = None

            for s in loader.iter_samples(limit=None):
                if s.get('metadata', {}).get('instance_id') == instance_id:
                    sample = s
                    break

            if not sample:
                return {
                    'instance_id': instance_id,
                    'success': False,
                    'error': f'Instance not found: {instance_id}',
                    'elapsed_seconds': time.time() - start_time,
                }

            print(f"Repo: {sample['repo']}")

            # Setup repository
            print("\n[1/5] Setting up repository...")
            # Use unique directory per SLURM job to avoid conflicts
            task_id = os.environ.get('SLURM_ARRAY_TASK_ID', os.environ.get('SLURM_JOB_ID', 'local'))
            repos_root = f"./repos_temp_{task_id}"
            patcher = PatchLoader(sample=sample, repos_root=repos_root)
            repo_path = patcher.clone_repository()
            patch_result = patcher.apply_patch()

            if not patch_result['applied']:
                return {
                    'instance_id': instance_id,
                    'success': False,
                    'error': 'Failed to apply patch',
                    'elapsed_seconds': time.time() - start_time,
                }

            # Apply test patch
            test_patch = sample.get('metadata', {}).get('test_patch', '')
            if test_patch and test_patch.strip():
                try:
                    patcher.apply_additional_patch(test_patch)
                    print("  ✓ Test patch applied")
                except Exception as e:
                    print(f"  ⚠️ Test patch failed: {e}")

            # Build container
            print("\n[2/5] Building/loading container...")
            docker_image = self.resolver.find_available_image(instance_id, check_existence=False)

            build_result = self.builder.build_instance(
                instance_id=instance_id,
                force_rebuild=False,
                check_docker_exists=False
            )

            if not build_result.success:
                return {
                    'instance_id': instance_id,
                    'success': False,
                    'error': f'Container build failed: {build_result.error_message}',
                    'elapsed_seconds': time.time() - start_time,
                }

            container_path = build_result.sif_path
            from_cache = build_result.from_cache
            print(f"  ✓ Container ready ({'cached' if from_cache else 'built'})")

            # Install dependencies
            print("\n[3/5] Installing dependencies...")
            install_result = test_patch_singularity.install_package_in_singularity(
                repo_path=Path(repo_path),
                image_path=str(container_path)
            )

            if self.config['enable_fuzzing']:
                test_patch_singularity.install_pytest_cov_in_singularity(
                    repo_path=Path(repo_path),
                    image_path=str(container_path)
                )

            if self.config['enable_rules']:
                rules_packages_dir = Path(repo_path) / ".pip_packages_rules"
                rules_packages_dir.mkdir(exist_ok=True)

            print("  ✓ Dependencies installed")

            # Initialize results
            results = {
                'instance_id': instance_id,
                'success': True,
                'repo': sample['repo'],
                'container_from_cache': from_cache,
                'enabled_modules': {
                    'static': self.config['enable_static'],
                    'fuzzing': self.config['enable_fuzzing'],
                    'rules': self.config['enable_rules'],
                },
                'config': {
                    'static': {
                        'threshold': self.config['static_threshold'],
                    },
                    'fuzzing': {
                        'coverage_threshold': self.config['coverage_threshold'],
                    },
                    'rules': {
                        'fail_on_high_severity': self.config['rules_fail_on_high_severity'],
                    },
                },
            }

            # Run analysis modules
            print("\n[4/5] Running analysis modules...")

            if self.config['enable_static']:
                results['static'] = self._run_static(repo_path, sample['patch'])

            if self.config['enable_fuzzing']:
                results['fuzzing'] = self._run_fuzzing(repo_path, sample, container_path)

            if self.config['enable_rules']:
                results['rules'] = self._run_rules(repo_path, sample['patch'], container_path)

            # Calculate verdict
            print("\n[5/5] Calculating verdict...")
            verdict_data = self._calculate_verdict(results)
            results.update(verdict_data)

            results['elapsed_seconds'] = time.time() - start_time

            print(f"\n{'='*60}")
            print(f"VERDICT: {results['verdict']}")
            print(f"Score: {results['overall_score']:.1f}/100")
            print(f"Time: {results['elapsed_seconds']:.1f}s")
            print(f"{'='*60}\n")

            return results

        except Exception as e:
            print(f"\n✗ ERROR: {str(e)}")
            traceback.print_exc()
            return {
                'instance_id': instance_id,
                'success': False,
                'error': str(e),
                'elapsed_seconds': time.time() - start_time,
            }

    def _run_static(self, repo_path: str, patch: str) -> dict:
        """Run static analysis."""
        print("  → Static analysis...")

        static_config = {
            'checks': {'pylint': True, 'flake8': True, 'radon': True, 'mypy': True, 'bandit': True},
            'weights': {'pylint': 0.5, 'flake8': 0.15, 'radon': 0.25, 'mypy': 0.05, 'bandit': 0.05}
        }

        cq_results = code_quality.analyze(str(repo_path), patch, static_config)
        sqi_data = cq_results.get('sqi', {})
        sqi_score = sqi_data.get('SQI', 0) / 100.0

        passed = sqi_score >= self.config['static_threshold']
        print(f"    SQI: {sqi_score*100:.1f}/100 {'✅' if passed else '❌'}")

        # Build detailed output with all analyzer results
        result = {
            'sqi_score': sqi_score * 100,
            'passed': passed,
            'sqi_breakdown': sqi_data.get('breakdown', {}),
            'meta': cq_results.get('meta', {}),
            'config': static_config,
        }

        # Add detailed results from each analyzer
        analyzers = {}

        # Pylint details
        if cq_results.get('pylint'):
            pylint_data = cq_results['pylint']
            total_issues = sum(len(issues) for issues in pylint_data.values())
            analyzers['pylint'] = {
                'enabled': True,
                'total_issues': total_issues,
                'by_file': pylint_data,
            }

        # Flake8 details
        if cq_results.get('flake8'):
            analyzers['flake8'] = {
                'enabled': True,
                'total_issues': len(cq_results['flake8']),
                'issues': cq_results['flake8'],
            }

        # Radon details
        if cq_results.get('radon'):
            radon_data = cq_results['radon']
            analyzers['radon'] = {
                'enabled': True,
                'avg_mi': radon_data.get('mi_avg', 0),
                'complexity': radon_data.get('complexity', {}),
            }

        # Mypy details
        if cq_results.get('mypy'):
            mypy_issues = cq_results['mypy']
            error_count = sum(1 for issue in mypy_issues if issue.get('severity') == 'error')
            analyzers['mypy'] = {
                'enabled': True,
                'total_errors': error_count,
                'total_issues': len(mypy_issues),
                'issues': mypy_issues,
            }

        # Bandit details
        if cq_results.get('bandit'):
            bandit_issues = cq_results['bandit']
            severity_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
            for issue in bandit_issues:
                severity = issue.get('issue_severity', 'MEDIUM').upper()
                if severity in severity_counts:
                    severity_counts[severity] += 1
            analyzers['bandit'] = {
                'enabled': True,
                'total_issues': len(bandit_issues),
                'severity_counts': severity_counts,
                'issues': bandit_issues,
            }

        result['analyzers'] = analyzers
        result['modified_files'] = cq_results.get('modified_files', [])

        return result

    def _run_fuzzing(self, repo_path: str, sample: dict, container_path: str) -> dict:
        """Run dynamic fuzzing."""
        print("  → Dynamic fuzzing...")

        # Analyze patch
        patch_analyzer = PatchAnalyzer()
        parsed_diff = parse_unified_diff(sample['patch'])
        modified_files = filter_paths_to_py(list(parsed_diff.keys()))

        if not modified_files:
            print("    No Python files modified")
            return {
                'tests_passed': True,
                'fuzzing_passed': True,
                'tests_generated': 0,
                'combined_coverage': 0.0,
                'passed': True,
            }

        first_file_path = modified_files[0]
        first_file = Path(repo_path) / first_file_path
        patched_code = first_file.read_text(encoding='utf-8')

        patch_analysis = patch_analyzer.parse_patch(sample['patch'], patched_code, file_path=first_file_path)

        # DEBUG: Check if patch analyzer found functions
        print(f"DEBUG: File has {len(patched_code.splitlines())} lines")
        print(f"DEBUG: changed_functions: {patch_analysis.changed_functions}")
        print(f"DEBUG: class_context: {patch_analysis.class_context}")
        print(f"DEBUG: all_changed_lines: {len(patch_analysis.all_changed_lines)} lines")
        coverage_source = patch_analysis.module_path.split('.')[0]

        # Run baseline tests
        import ast
        fail_to_pass = sample.get('metadata', {}).get('FAIL_TO_PASS', '[]')
        pass_to_pass = sample.get('metadata', {}).get('PASS_TO_PASS', '[]')

        try:
            f2p = ast.literal_eval(fail_to_pass) if isinstance(fail_to_pass, str) else fail_to_pass
            p2p = ast.literal_eval(pass_to_pass) if isinstance(pass_to_pass, str) else pass_to_pass
        except:
            f2p, p2p = [], []

        all_tests = f2p + p2p

        test_result = test_patch_singularity.run_tests_in_singularity(
            repo_path=Path(repo_path),
            tests=all_tests,
            image_path=str(container_path),
            collect_coverage=True,
            coverage_source=coverage_source,
        )

        tests_passed = (test_result['returncode'] == 0)

        # Analyze coverage
        baseline_coverage = 0.0
        baseline_covered_lines = set()

        if 'coverage_file' in test_result and test_result['coverage_file']:
            baseline_cov_file = Path(test_result['coverage_file'])
            if baseline_cov_file.exists():
                baseline_coverage_data = json.loads(baseline_cov_file.read_text())
                baseline_analysis = analyze_coverage_unified(
                    coverage_data=baseline_coverage_data,
                    patch_analysis=patch_analysis,
                    analyzer=CoverageAnalyzer(),
                    label="BASELINE"
                )
                if baseline_analysis:
                    baseline_coverage = baseline_analysis['line_coverage']
                    baseline_covered_lines = baseline_analysis['covered_lines']

        # Generate fuzzing tests
        print(f"DEBUG: Initializing test generator with repo_path={repo_path}")
        test_generator = HypothesisTestGenerator(repo_path=Path(repo_path))
        print(f"DEBUG: Generating tests for {len(patch_analysis.changed_functions)} functions")
        test_code = test_generator.generate_tests(patch_analysis, patched_code)
        test_count = test_code.count('def test_')
        print(f"DEBUG: Generated {test_count} tests")

        test_file = Path(repo_path) / "test_fuzzing_generated.py"
        test_file.write_text(test_code, encoding='utf-8')

        test_patch_singularity.install_hypothesis_in_singularity(
            repo_path=Path(repo_path),
            image_path=str(container_path)
        )

        fuzzing_result = test_patch_singularity.run_tests_in_singularity(
            repo_path=Path(repo_path),
            tests=["test_fuzzing_generated.py"],
            image_path=str(container_path),
            extra_env={"HYPOTHESIS_MAX_EXAMPLES": "50"},
            collect_coverage=True,
            coverage_source=coverage_source,
        )

        fuzzing_success = (fuzzing_result['returncode'] == 0)

        # Combined coverage
        combined_coverage = baseline_coverage
        if 'coverage_file' in fuzzing_result and fuzzing_result['coverage_file']:
            fuzzing_cov_file = Path(fuzzing_result['coverage_file'])
            if fuzzing_cov_file.exists():
                fuzzing_coverage_data = json.loads(fuzzing_cov_file.read_text())
                fuzzing_analysis = analyze_coverage_unified(
                    coverage_data=fuzzing_coverage_data,
                    patch_analysis=patch_analysis,
                    analyzer=CoverageAnalyzer(),
                    label="FUZZING"
                )
                if fuzzing_analysis:
                    combined_covered_lines = baseline_covered_lines | fuzzing_analysis['covered_lines']
                    all_changed = set(patch_analysis.all_changed_lines)
                    combined_coverage = len(combined_covered_lines) / len(all_changed) if all_changed else 0.0

        passed = combined_coverage >= self.config['coverage_threshold']

        print(f"    Tests: {'PASS' if tests_passed else 'FAIL'}, Fuzzing: {test_count} tests")
        print(f"    Coverage: {combined_coverage*100:.1f}% {'✅' if passed else '⚠️'}")

        # Calculate improvement
        improvement = (combined_coverage - baseline_coverage) * 100 if baseline_coverage >= 0 else 0.0

        return {
            'tests_passed': tests_passed,
            'fuzzing_passed': fuzzing_success,
            'tests_generated': test_count,
            'combined_coverage': combined_coverage * 100,
            'baseline_coverage': baseline_coverage * 100,
            'improvement': improvement,
            'passed': passed,
            'details': {
                'patch_analysis': {
                    'modified_files': modified_files,
                    'primary_file': first_file_path,
                    'total_changed_lines': len(patch_analysis.all_changed_lines),
                    'module_path': patch_analysis.module_path,
                },
                'baseline_tests': {
                    'count': len(all_tests),
                    'fail_to_pass': len(f2p),
                    'pass_to_pass': len(p2p),
                    'passed': tests_passed,
                    'returncode': test_result['returncode'],
                    'coverage': baseline_coverage * 100,
                    'covered_lines': len(baseline_covered_lines),
                },
                'fuzzing_tests': {
                    'count': test_count,
                    'passed': fuzzing_success,
                    'returncode': fuzzing_result['returncode'],
                },
            }
        }

    def _run_rules(self, repo_path: str, patch: str, container_path: str) -> dict:
        """Run verification rules."""
        print("  → Verification rules...")

        try:
            rules_result = test_patch_singularity.run_rules_in_singularity(
                repo_path=Path(repo_path),
                patch_str=patch,
                rule_ids=RULE_IDS,
                image_path=str(container_path),
                verifier_harness_path=Path.cwd(),
            )

            if 'results' in rules_result and rules_result['results']:
                rules_results = rules_result['results']

                all_findings = []
                failed_rules = []
                passed_rules = []

                # Process each rule result
                for result in rules_results:
                    if result.get('status') == 'failed':
                        failed_rules.append(result.get('name', 'unknown'))
                        all_findings.extend(result.get('findings', []))
                    elif result.get('status') == 'passed':
                        passed_rules.append(result.get('name', 'unknown'))

                high_severity_count = sum(1 for f in all_findings if f.get('severity') == 'high')
                medium_severity_count = sum(1 for f in all_findings if f.get('severity') == 'medium')
                low_severity_count = sum(1 for f in all_findings if f.get('severity') == 'low')

                passed = not (high_severity_count > 0 and self.config['rules_fail_on_high_severity'])

                print(f"    Rules: {len(rules_results) - len(failed_rules)}/{len(rules_results)} passed")
                print(f"    Findings: {len(all_findings)} (High: {high_severity_count}) {'✅' if passed else '❌'}")

                # Organize findings by severity and taxonomy
                findings_by_severity = {
                    'high': [f for f in all_findings if f.get('severity') == 'high'],
                    'medium': [f for f in all_findings if f.get('severity') == 'medium'],
                    'low': [f for f in all_findings if f.get('severity') == 'low'],
                }

                # Organize findings by taxonomy tags
                findings_by_taxonomy = {}
                for finding in all_findings:
                    for tag in finding.get('taxonomy_tags', []):
                        if tag not in findings_by_taxonomy:
                            findings_by_taxonomy[tag] = []
                        findings_by_taxonomy[tag].append(finding)

                return {
                    'total_rules': len(rules_results),
                    'passed_rules': len(passed_rules),
                    'failed_rules': len(failed_rules),
                    'findings_count': len(all_findings),
                    'high_severity_count': high_severity_count,
                    'medium_severity_count': medium_severity_count,
                    'low_severity_count': low_severity_count,
                    'passed': passed,
                    'rule_results': rules_results,  # Include all individual rule results
                    'findings_by_severity': findings_by_severity,
                    'findings_by_taxonomy': findings_by_taxonomy,
                }
            else:
                return {
                    'total_rules': 0,
                    'passed_rules': 0,
                    'failed_rules': 0,
                    'findings_count': 0,
                    'high_severity_count': 0,
                    'medium_severity_count': 0,
                    'low_severity_count': 0,
                    'passed': True,
                    'rule_results': [],
                    'findings_by_severity': {'high': [], 'medium': [], 'low': []},
                    'findings_by_taxonomy': {},
                }
        except Exception as e:
            print(f"    ⚠️ Rules error: {e}")
            return {
                'total_rules': 0,
                'passed_rules': 0,
                'failed_rules': 0,
                'findings_count': 0,
                'high_severity_count': 0,
                'medium_severity_count': 0,
                'low_severity_count': 0,
                'passed': True,
                'error': str(e),
                'rule_results': [],
                'findings_by_severity': {'high': [], 'medium': [], 'low': []},
                'findings_by_taxonomy': {},
            }

    def _calculate_verdict(self, results: dict) -> dict:
        """Calculate overall verdict."""
        static_passed = results.get('static', {}).get('passed', True)
        tests_passed = results.get('fuzzing', {}).get('tests_passed', True)
        fuzzing_passed = results.get('fuzzing', {}).get('passed', True)
        rules_passed = results.get('rules', {}).get('passed', True)

        # Weighted score
        weights = {
            'static': 30 if self.config['enable_static'] else 0,
            'tests': 40,
            'fuzzing': 15 if self.config['enable_fuzzing'] else 0,
            'coverage': 10 if self.config['enable_fuzzing'] else 0,
            'rules': 5 if self.config['enable_rules'] else 0,
        }

        total_weight = sum(weights.values())
        for key in weights:
            weights[key] = (weights[key] / total_weight) * 100

        # Add weights to config
        if 'config' in results:
            results['config']['verdict_weights'] = weights.copy()

        sqi_score = results.get('static', {}).get('sqi_score', 0)
        combined_coverage = results.get('fuzzing', {}).get('combined_coverage', 0)

        overall_score = (
            (sqi_score if self.config['enable_static'] else 0) * (weights['static'] / 100) +
            (100 if tests_passed else 0) * (weights['tests'] / 100) +
            (100 if results.get('fuzzing', {}).get('fuzzing_passed', True) else 0) * (weights['fuzzing'] / 100) +
            (combined_coverage if self.config['enable_fuzzing'] else 0) * (weights['coverage'] / 100) +
            (100 if rules_passed else 0) * (weights['rules'] / 100)
        )

        # Determine verdict
        failed_checks = []
        if not static_passed:
            failed_checks.append("Static")
        if not tests_passed:
            failed_checks.append("Tests")
        if not fuzzing_passed:
            failed_checks.append("Coverage")
        if not rules_passed:
            failed_checks.append("Rules")

        if failed_checks:
            if any(c in failed_checks for c in ["Static", "Tests", "Rules"]):
                verdict = "❌ REJECT"
                reason = f"Failed: {', '.join(failed_checks)}"
            else:
                verdict = "⚠️ WARNING"
                reason = f"Warnings: {', '.join(failed_checks)}"
        else:
            if overall_score >= 80:
                verdict = "✅ EXCELLENT"
                reason = "All checks passed"
            elif overall_score >= 60:
                verdict = "✓ GOOD"
                reason = "All checks passed"
            else:
                verdict = "⚠️ FAIR"
                reason = "Passed but low score"

        return {
            'overall_score': overall_score,
            'verdict': verdict,
            'reason': reason,
        }


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Integrated pipeline SLURM worker")

    parser.add_argument('--instance-id', required=True, help='SWE-bench instance ID')
    parser.add_argument('--output', type=Path, required=True, help='Output JSON file')

    # Modules
    parser.add_argument('--enable-static', action='store_true', help='Enable static analysis')
    parser.add_argument('--enable-fuzzing', action='store_true', help='Enable fuzzing')
    parser.add_argument('--enable-rules', action='store_true', help='Enable rules')

    # Thresholds
    parser.add_argument('--static-threshold', type=float, default=0.5)
    parser.add_argument('--coverage-threshold', type=float, default=0.5)

    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    config = {
        'enable_static': args.enable_static,
        'enable_fuzzing': args.enable_fuzzing,
        'enable_rules': args.enable_rules,
        'static_threshold': args.static_threshold,
        'coverage_threshold': args.coverage_threshold,
        'rules_fail_on_high_severity': True,
    }

    worker = IntegratedPipelineWorker(config)
    result = worker.run(args.instance_id)

    # Save results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Results saved to: {args.output}")

    # Exit with appropriate code
    return 0 if result['success'] else 1


if __name__ == "__main__":
    sys.exit(main())
