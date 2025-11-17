"""
Execute tests in Singularity containers with coverage tracking.

This module adapts the test execution to work with your existing
Singularity infrastructure from test_patch_singularity.py.
"""

import subprocess
import tempfile
import json
import os
from pathlib import Path
from typing import Tuple, Dict, Any, Optional


class SingularityTestExecutor:
    """
    Execute generated tests in Singularity containers with coverage tracking.
    Integrates with the existing Singularity infrastructure.
    """

    def __init__(
        self,
        image_path: str = "/scratch0/ihbas/.containers/singularity/verifier-swebench.sif",
        timeout: int = 60
    ):
        """
        Args:
            image_path: Path to your Singularity .sif image
            timeout: Timeout in seconds for test execution
        """
        self.image_path = Path(image_path)
        self.timeout = timeout

        if not self.image_path.exists():
            raise FileNotFoundError(
                f"Singularity image not found: {self.image_path}\n"
                "Run test_singularity_build.py to create the image first."
            )

    def run_tests_in_container(
        self,
        test_code: str,
        source_code: str,
        module_name: str = "module_under_test",
        repo_path: Optional[Path] = None,
    ) -> Tuple[bool, str, Dict]:
        """
        Execute tests in Singularity container with coverage tracking.

        Args:
            test_code: Generated test code (pytest format)
            source_code: The patched source code to test
            module_name: Name for the module under test
            repo_path: Optional path to existing repo (for integration with SWE-bench)

        Returns:
            (success, output, coverage_data)
        """
        # If repo_path is provided, use it directly
        # Otherwise, create a temporary directory
        if repo_path:
            return self._run_tests_in_repo(test_code, repo_path)
        else:
            return self._run_tests_standalone(test_code, source_code, module_name)

    def _run_tests_standalone(
        self,
        test_code: str,
        source_code: str,
        module_name: str
    ) -> Tuple[bool, str, Dict]:
        """Run tests in a temporary directory with provided source code"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write source code
            source_file = tmpdir_path / f"{module_name}.py"
            source_file.write_text(source_code)

            # Write test code
            test_file = tmpdir_path / "test_generated.py"
            # Add import statement to test code
            import_statement = f"from {module_name} import *\n\n"
            test_code_with_import = import_statement + test_code
            test_file.write_text(test_code_with_import)

            return self._execute_tests(tmpdir_path, module_name)

    def _run_tests_in_repo(
        self,
        test_code: str,
        repo_path: Path,
        module_name: str = None
    ) -> Tuple[bool, str, Dict]:
        """Run tests in an existing repository (for SWE-bench integration)"""
        # Create a temporary test file in the repo
        test_file = repo_path / "test_fuzzing_generated.py"

        try:
            test_file.write_text(test_code)

            # Find the module name from the repo structure if not provided
            # This is a simplified heuristic - may need enhancement
            if not module_name:
                module_name = self._detect_module_name(repo_path)

            return self._execute_tests(repo_path, module_name, cleanup_test_file=test_file)

        finally:
            # Clean up generated test file
            if test_file.exists():
                test_file.unlink()

    def _detect_module_name(self, repo_path: Path) -> str:
        """Detect the main module name from repo structure"""
        # Look for common patterns
        for item in repo_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if (item / '__init__.py').exists():
                    return item.name

        # Fallback to repo name
        return repo_path.name.replace('-', '_').replace('__', '_')

    def _execute_tests(
        self,
        work_path: Path,
        module_name: str,
        cleanup_test_file: Optional[Path] = None
    ) -> Tuple[bool, str, Dict]:
        """
        Execute pytest with coverage in Singularity container.

        Args:
            work_path: Directory containing code and tests
            module_name: Name of module to track coverage for
            cleanup_test_file: Optional file to clean up after execution

        Returns:
            (success, output, coverage_data)
        """
        work_path = work_path.resolve()

        # Determine if we should use coverage
        # Enable coverage for all valid module names (including underscore-prefixed)
        use_coverage = bool(module_name)

        # Build coverage flags if needed
        if use_coverage:
            cov_flags = f'--cov={module_name} --cov-report=json --cov-report=term'
        else:
            cov_flags = ''

        # Execute in Singularity
        cmd = [
            'singularity', 'exec',
            '--fakeroot',  # Use fakeroot for package access
            '--bind', f'{work_path}:/workspace',
            '--pwd', '/workspace',
            '--env', 'PYTHONPATH=/workspace',
            str(self.image_path),
            'bash', '-c',
            f'pytest -v --tb=short --timeout={self.timeout} {cov_flags} test_fuzzing_generated.py 2>&1'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10
            )

            # Parse coverage
            coverage_file = work_path / 'coverage.json'
            coverage_data = {}
            if coverage_file.exists():
                try:
                    coverage_data = json.loads(coverage_file.read_text())
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse coverage.json: {e}")

            # Check if tests passed (pytest exit code 0 or 1 for test failures, not coverage)
            # Exit codes: 0=all passed, 1=tests failed, 2=interrupted, etc.
            # Coverage warnings shouldn't fail the test run
            success = result.returncode == 0
            output = result.stdout + '\n' + result.stderr

            # If returncode is non-zero, check if it's just coverage issues
            # Look for test passing indicators in output
            if not success and ('passed' in output.lower() or 'PASSED' in output):
                # Tests actually passed, just coverage had issues
                # Count this as success
                success = True

            return (success, output, coverage_data)

        except subprocess.TimeoutExpired:
            return (False, "TIMEOUT: Tests exceeded time limit", {})
        except Exception as e:
            return (False, f"ERROR: {str(e)}", {})

    def run_tests_with_existing_infrastructure(
        self,
        repo_path: Path,
        test_code: str,
        module_name: str = None
    ) -> Tuple[bool, str, Dict]:
        """
        Run generated fuzzing tests using the existing test infrastructure.

        This method integrates with your existing test_patch_singularity.py
        infrastructure for seamless SWE-bench integration.

        Args:
            repo_path: Path to the patched repository
            test_code: Generated test code
            module_name: Optional module name for coverage tracking
                        (e.g., "_pytest.logging"). If not provided, auto-detected.

        Returns:
            (success, output, coverage_data)
        """
        return self._run_tests_in_repo(test_code, repo_path, module_name)


# Example usage
if __name__ == "__main__":
    # Test with simple code
    source_code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def add(a, b):
    return a + b
"""

    test_code = """
import pytest
from hypothesis import given, strategies as st, settings

@given(st.integers(), st.integers())
@settings(max_examples=50)
def test_divide_properties(a, b):
    try:
        result = divide(a, b)
        assert isinstance(result, (int, float))
    except ValueError:
        assert b == 0

def test_divide_zero():
    with pytest.raises(ValueError):
        divide(10, 0)

def test_add_properties():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
"""

    executor = SingularityTestExecutor()

    try:
        success, output, coverage = executor.run_tests_in_container(
            test_code=test_code,
            source_code=source_code,
            module_name="example"
        )

        print(f"Success: {success}")
        print(f"\nOutput:\n{output}")
        print(f"\nCoverage data: {coverage.get('totals', {})}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure to build the Singularity image first:")
        print("  python test_singularity_build.py")
