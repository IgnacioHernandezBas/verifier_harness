"""
Podman-based Test Executor for SWE-bench Evaluation

This module integrates the verified SWE-bench test execution methodology
into the verifier harness. It supports:
1. Running official SWE-bench tests (from eval.sh)
2. Running custom tests (fuzzing, invariance)
3. Executing in isolated Docker/Podman containers

The execution follows the exact SWE-bench methodology:
- Apply code patch
- Apply test patches from eval.sh
- Run tests
- Check exit code (0 = PASS, non-zero = FAIL)
"""

import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class TestType(Enum):
    """Types of tests that can be executed"""
    SWEBENCH = "swebench"       # Official SWE-bench tests from eval.sh
    FUZZING = "fuzzing"         # Hypothesis-generated fuzzing tests
    INVARIANCE = "invariance"   # Property-based invariance tests
    CUSTOM = "custom"           # Custom test code


@dataclass
class ExecutionResult:
    """Result of a test execution"""
    success: bool
    exit_code: int
    test_output: str
    coverage_data: Optional[Dict] = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'exit_code': self.exit_code,
            'test_output': self.test_output[:5000] if self.test_output else '',
            'coverage_data': self.coverage_data,
            'error': self.error,
            'execution_time': self.execution_time
        }


class PodmanTestExecutor:
    """
    Execute tests in Podman containers using SWE-bench methodology.

    This executor can run:
    1. Official SWE-bench tests (using eval.sh from experiment logs)
    2. Custom fuzzing tests
    3. Invariance/property-based tests

    All tests run inside the official SWE-bench Docker images.
    """

    def __init__(
        self,
        scratch_dir: str = "/scratch0/ihbas",
        timeout: int = 300,
        enable_coverage: bool = True
    ):
        """
        Initialize the Podman executor.

        Args:
            scratch_dir: Local scratch directory for container operations
            timeout: Default timeout for test execution (seconds)
            enable_coverage: Whether to collect coverage data
        """
        self.scratch_dir = Path(scratch_dir)
        self.timeout = timeout
        self.enable_coverage = enable_coverage

        # Verify scratch directory exists (needed for Podman)
        if not self.scratch_dir.exists():
            raise RuntimeError(
                f"Scratch directory {scratch_dir} not found. "
                "This executor requires local storage (not NFS)."
            )

    def get_docker_image(self, instance_id: str) -> str:
        """
        Convert instance ID to Docker image name.

        Args:
            instance_id: SWE-bench instance ID (e.g., 'django__django-12345')

        Returns:
            Docker image name
        """
        org = instance_id.split('__')[0]
        rest = instance_id.split('__')[1]
        repo_and_num = rest.replace('__', '_')
        return f"docker.io/swebench/sweb.eval.x86_64.{org}_1776_{repo_and_num}:latest"

    def run_swebench_tests(
        self,
        instance_id: str,
        patch_diff: str,
        eval_script_path: Path,
        output_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """
        Run official SWE-bench tests for an instance.

        This follows the exact SWE-bench evaluation methodology:
        1. Apply the code patch
        2. Apply test patches from eval.sh
        3. Run the test command from eval.sh
        4. Return exit code (0 = PASS)

        Args:
            instance_id: SWE-bench instance ID
            patch_diff: The code patch to apply (unified diff format)
            eval_script_path: Path to the eval.sh file
            output_dir: Directory to store outputs (optional)

        Returns:
            ExecutionResult with test outcome
        """
        import time
        start_time = time.time()

        docker_image = self.get_docker_image(instance_id)

        # Setup directories
        if output_dir is None:
            output_dir = self.scratch_dir / "podman_results" / instance_id
        output_dir.mkdir(parents=True, exist_ok=True)

        patch_dir = self.scratch_dir / "patches" / instance_id
        patch_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy eval.sh and patch to scratch
            shutil.copy(eval_script_path, patch_dir / "eval.sh")
            (patch_dir / "patch.diff").write_text(patch_diff)

            # Pull the Docker image
            pull_result = subprocess.run(
                ["podman", "pull", docker_image],
                capture_output=True,
                text=True,
                timeout=300
            )

            if pull_result.returncode != 0:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    test_output="",
                    error=f"Failed to pull image: {pull_result.stderr}",
                    execution_time=time.time() - start_time
                )

            # Build the container command
            container_script = self._build_swebench_test_script()

            # Run the container
            run_result = subprocess.run(
                [
                    "podman", "run", "--rm",
                    "-v", f"{patch_dir}:/patch:ro",
                    "-v", f"{output_dir}:/output",
                    "--workdir", "/testbed",
                    docker_image,
                    "/bin/bash", "-c", container_script
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Read test output
            test_output_file = output_dir / "test_output.txt"
            test_output = ""
            if test_output_file.exists():
                test_output = test_output_file.read_text()

            # Read exit code
            exit_code_file = output_dir / "exit_code.txt"
            exit_code = run_result.returncode
            if exit_code_file.exists():
                try:
                    exit_code = int(exit_code_file.read_text().strip())
                except ValueError:
                    pass

            # Read coverage if enabled
            coverage_data = None
            if self.enable_coverage:
                coverage_file = output_dir / "coverage.json"
                if coverage_file.exists():
                    coverage_data = json.loads(coverage_file.read_text())

            return ExecutionResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                test_output=test_output,
                coverage_data=coverage_data,
                execution_time=time.time() - start_time
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                test_output="",
                error=f"Timeout after {self.timeout}s",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                test_output="",
                error=str(e),
                execution_time=time.time() - start_time
            )
        finally:
            # Cleanup patch directory
            if patch_dir.exists():
                shutil.rmtree(patch_dir, ignore_errors=True)

    def run_custom_tests(
        self,
        instance_id: str,
        patch_diff: str,
        test_code: str,
        test_type: TestType = TestType.CUSTOM,
        output_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """
        Run custom tests (fuzzing, invariance, etc.) in the SWE-bench container.

        Args:
            instance_id: SWE-bench instance ID
            patch_diff: The code patch to apply
            test_code: Python test code to execute
            test_type: Type of test being run
            output_dir: Directory to store outputs

        Returns:
            ExecutionResult with test outcome
        """
        import time
        start_time = time.time()

        docker_image = self.get_docker_image(instance_id)

        # Setup directories
        if output_dir is None:
            output_dir = self.scratch_dir / "podman_results" / instance_id / test_type.value
        output_dir.mkdir(parents=True, exist_ok=True)

        patch_dir = self.scratch_dir / "patches" / instance_id
        patch_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write patch and test code to scratch
            (patch_dir / "patch.diff").write_text(patch_diff)
            (patch_dir / "custom_tests.py").write_text(test_code)

            # Pull the Docker image
            pull_result = subprocess.run(
                ["podman", "pull", docker_image],
                capture_output=True,
                text=True,
                timeout=300
            )

            if pull_result.returncode != 0:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    test_output="",
                    error=f"Failed to pull image: {pull_result.stderr}",
                    execution_time=time.time() - start_time
                )

            # Build the container command for custom tests
            container_script = self._build_custom_test_script(
                enable_coverage=self.enable_coverage
            )

            # Run the container
            run_result = subprocess.run(
                [
                    "podman", "run", "--rm",
                    "-v", f"{patch_dir}:/patch:ro",
                    "-v", f"{output_dir}:/output",
                    "--workdir", "/testbed",
                    docker_image,
                    "/bin/bash", "-c", container_script
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Read test output
            test_output_file = output_dir / "test_output.txt"
            test_output = ""
            if test_output_file.exists():
                test_output = test_output_file.read_text()

            # Read exit code
            exit_code_file = output_dir / "exit_code.txt"
            exit_code = run_result.returncode
            if exit_code_file.exists():
                try:
                    exit_code = int(exit_code_file.read_text().strip())
                except ValueError:
                    pass

            # Read coverage if enabled
            coverage_data = None
            if self.enable_coverage:
                coverage_file = output_dir / "coverage.json"
                if coverage_file.exists():
                    try:
                        coverage_data = json.loads(coverage_file.read_text())
                    except json.JSONDecodeError:
                        pass

            return ExecutionResult(
                success=(exit_code == 0),
                exit_code=exit_code,
                test_output=test_output,
                coverage_data=coverage_data,
                execution_time=time.time() - start_time
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                test_output="",
                error=f"Timeout after {self.timeout}s",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                test_output="",
                error=str(e),
                execution_time=time.time() - start_time
            )
        finally:
            # Cleanup patch directory
            if patch_dir.exists():
                shutil.rmtree(patch_dir, ignore_errors=True)

    def _build_swebench_test_script(self) -> str:
        """Build the bash script for running SWE-bench tests inside container"""
        return r'''
# Apply the code patch first
if [ -f /patch/patch.diff ]; then
    git apply -v /patch/patch.diff >> /output/patch.log 2>&1 || {
        echo "PATCH_FAILED" > /output/status.txt
        echo "1" > /output/exit_code.txt
        exit 1
    }
fi

# Run test setup and tests from eval.sh
if [ -f /patch/eval.sh ]; then
    # Activate environment
    source /opt/miniconda3/bin/activate 2>/dev/null || true
    conda activate testbed 2>/dev/null || true

    # Apply test patches (git checkout commands)
    grep "^git checkout .* tests/" /patch/eval.sh | while read -r cmd; do
        eval "$cmd" >> /output/patch.log 2>&1 || true
    done

    # Apply inline git patches
    sed -n "/git apply -v - <<'EOF_/,/^EOF_/p" /patch/eval.sh | \
        sed "1d;\$d" | git apply -v >> /output/patch.log 2>&1 || true

    # Extract and run the test command (between >>>>> markers)
    test_cmd=$(sed -n "/>>>>> Start Test Output/,/>>>>> End Test Output/p" /patch/eval.sh | \
               grep -v ">>>>>" | grep -v "^:" | grep -v "^$" | head -1)

    if [ -n "$test_cmd" ]; then
        eval "$test_cmd" > /output/test_output.txt 2>&1
        exit_code=$?
    else
        pytest > /output/test_output.txt 2>&1
        exit_code=$?
    fi

    # Save exit code
    echo "$exit_code" > /output/exit_code.txt
    exit $exit_code
else
    echo "ERROR: No eval.sh found" > /output/test_output.txt
    echo "1" > /output/exit_code.txt
    exit 1
fi
'''

    def _build_custom_test_script(self, enable_coverage: bool = True) -> str:
        """Build the bash script for running custom tests inside container"""
        coverage_prefix = ""
        coverage_report = ""

        if enable_coverage:
            coverage_prefix = "coverage run --source=. -m "
            coverage_report = """
# Generate coverage report
coverage json -o /output/coverage.json 2>/dev/null || true
"""

        return f'''
# Apply the code patch first
if [ -f /patch/patch.diff ]; then
    git apply -v /patch/patch.diff >> /output/patch.log 2>&1 || {{
        echo "PATCH_FAILED" > /output/status.txt
        echo "1" > /output/exit_code.txt
        exit 1
    }}
fi

# Activate environment
source /opt/miniconda3/bin/activate 2>/dev/null || true
conda activate testbed 2>/dev/null || true

# Install test dependencies if needed
pip install hypothesis pytest-timeout coverage 2>/dev/null || true

# Copy test file
cp /patch/custom_tests.py /testbed/custom_tests.py

# Run tests
{coverage_prefix}pytest /testbed/custom_tests.py -v --timeout=60 > /output/test_output.txt 2>&1
exit_code=$?

echo "$exit_code" > /output/exit_code.txt

{coverage_report}

exit $exit_code
'''


class IntegratedTestRunner:
    """
    High-level interface for running all test types on a patch.

    Combines:
    1. SWE-bench official tests
    2. Fuzzing tests
    3. Invariance tests
    """

    def __init__(
        self,
        experiment_logs_dir: str,
        scratch_dir: str = "/scratch0/ihbas",
        timeout: int = 300
    ):
        """
        Initialize the integrated test runner.

        Args:
            experiment_logs_dir: Path to SWE-bench experiment logs
            scratch_dir: Local scratch directory for Podman
            timeout: Test timeout in seconds
        """
        self.experiment_logs_dir = Path(experiment_logs_dir)
        self.executor = PodmanTestExecutor(
            scratch_dir=scratch_dir,
            timeout=timeout
        )

    def run_all_tests(
        self,
        instance_id: str,
        patch_diff: str,
        fuzzing_tests: Optional[str] = None,
        invariance_tests: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run all available tests on a patch.

        Args:
            instance_id: SWE-bench instance ID
            patch_diff: The code patch to evaluate
            fuzzing_tests: Optional fuzzing test code
            invariance_tests: Optional invariance test code

        Returns:
            Combined results from all test types
        """
        results = {
            'instance_id': instance_id,
            'swebench': None,
            'fuzzing': None,
            'invariance': None,
            'overall_verdict': 'UNKNOWN'
        }

        # 1. Run SWE-bench official tests
        eval_script = self.experiment_logs_dir / instance_id / "eval.sh"
        if eval_script.exists():
            swebench_result = self.executor.run_swebench_tests(
                instance_id=instance_id,
                patch_diff=patch_diff,
                eval_script_path=eval_script
            )
            results['swebench'] = swebench_result.to_dict()

        # 2. Run fuzzing tests if provided
        if fuzzing_tests:
            fuzzing_result = self.executor.run_custom_tests(
                instance_id=instance_id,
                patch_diff=patch_diff,
                test_code=fuzzing_tests,
                test_type=TestType.FUZZING
            )
            results['fuzzing'] = fuzzing_result.to_dict()

        # 3. Run invariance tests if provided
        if invariance_tests:
            invariance_result = self.executor.run_custom_tests(
                instance_id=instance_id,
                patch_diff=patch_diff,
                test_code=invariance_tests,
                test_type=TestType.INVARIANCE
            )
            results['invariance'] = invariance_result.to_dict()

        # Determine overall verdict
        results['overall_verdict'] = self._compute_verdict(results)

        return results

    def _compute_verdict(self, results: Dict) -> str:
        """
        Compute overall verdict from all test results.

        Priority:
        1. SWE-bench tests must pass
        2. Fuzzing tests (if run) should pass
        3. Invariance tests (if run) should pass
        """
        # SWE-bench is the primary indicator
        if results['swebench']:
            if not results['swebench']['success']:
                return 'FAIL'

        # Check fuzzing results
        if results['fuzzing']:
            if not results['fuzzing']['success']:
                return 'FAIL_FUZZING'

        # Check invariance results
        if results['invariance']:
            if not results['invariance']['success']:
                return 'FAIL_INVARIANCE'

        # All passed
        if results['swebench'] and results['swebench']['success']:
            return 'PASS'

        return 'UNKNOWN'
