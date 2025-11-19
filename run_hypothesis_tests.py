#!/usr/bin/env python3
"""
Run Hypothesis-based fuzzing tests in Singularity container.
Generates tests, writes them to a temporary file, and executes them.
"""

import subprocess
import tempfile
from pathlib import Path

def run_hypothesis_tests(
    container_path: str,
    repo_path: Path,
    test_code: str,
    module_name: str = None,
    timeout: int = 300
) -> dict:
    """
    Execute Hypothesis-generated fuzzing tests in container.
    
    Args:
        container_path: Path to .sif container
        repo_path: Path to repository
        test_code: Python code containing Hypothesis tests
        module_name: Module to test (for coverage)
        timeout: Test timeout in seconds
        
    Returns:
        dict with test results and coverage data
    """
    
    pip_base = Path("/fs/nexus-scratch/ihbas/.local/pip_packages")
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='_hypothesis_test.py',
        dir=repo_path,
        delete=False
    ) as f:
        f.write(test_code)
        test_file = Path(f.name)
    
    try:
        # Build pytest command with coverage if module specified
        pytest_args = ["-xvs", str(test_file.name)]
        
        if module_name:
            pytest_args.extend([
                f"--cov={module_name}",
                "--cov-report=json:/workspace/coverage.json"
            ])
        
        # Run tests in container
        run_cmd = [
            "singularity", "exec",
            "--writable-tmpfs",
            "--bind", f"{repo_path}:/workspace",
            "--bind", f"{pip_base}:/pip_install_base",
            "--pwd", "/workspace",
            "--env", "PYTHONPATH=/workspace",
            "--env", "PYTHONUSERBASE=/pip_install_base",
            container_path,
            "python", "-m", "pytest"
        ] + pytest_args
        
        print(f"Running Hypothesis tests...")
        print(f"  Test file: {test_file.name}")
        print(f"  Module: {module_name or 'N/A'}")
        
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Parse coverage if available
        coverage_data = {}
        coverage_file = repo_path / "coverage.json"
        if coverage_file.exists():
            import json
            with open(coverage_file) as f:
                coverage_data = json.load(f)
            coverage_file.unlink()  # Clean up
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "coverage": coverage_data,
            "test_file": str(test_file)
        }
        
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()

def generate_and_run_hypothesis_tests(
    container_path: str,
    repo_path: Path,
    patch_analysis,
    patched_code: str,
    timeout: int = 300
) -> dict:
    """
    Generate Hypothesis tests from patch analysis and run them.
    
    This is the high-level function you'd call from your notebook.
    """
    from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator
    
    # Generate tests
    print("Generating Hypothesis tests from patch...")
    test_generator = HypothesisTestGenerator()
    test_code = test_generator.generate_tests(patch_analysis, patched_code)
    test_count = test_code.count('def test_')
    
    print(f"  Generated {test_count} Hypothesis-based tests")
    
    if test_count == 0:
        return {
            "success": True,
            "returncode": 0,
            "stdout": "No tests generated",
            "stderr": "",
            "coverage": {},
            "test_count": 0
        }
    
    # Run tests
    module_name = patch_analysis.module_path if patch_analysis else None
    result = run_hypothesis_tests(
        container_path, 
        repo_path, 
        test_code, 
        module_name,
        timeout
    )
    result["test_count"] = test_count
    
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: run_hypothesis_tests.py <container> <repo_path> <test_file>")
        sys.exit(1)
    
    container = sys.argv[1]
    repo = Path(sys.argv[2])
    test_file = sys.argv[3]
    
    with open(test_file) as f:
        test_code = f.read()
    
    result = run_hypothesis_tests(container, repo, test_code)
    
    print(f"\n{'✓' if result['success'] else '✗'} Tests {'passed' if result['success'] else 'failed'}")
    sys.exit(0 if result['success'] else 1)
