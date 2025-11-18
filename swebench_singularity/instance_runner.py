"""
Instance Runner for SWE-bench evaluations.

Executes tests for specific SWE-bench instances using Singularity containers.
Integrates with the existing evaluation pipeline and change-aware fuzzing system.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from .config import Config
from .singularity_builder import SingularityBuilder

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of running tests for an instance."""

    instance_id: str
    success: bool
    passed_tests: int
    failed_tests: int
    total_tests: int
    execution_time_seconds: float
    error_message: Optional[str]
    stdout: Optional[str]
    stderr: Optional[str]
    exit_code: int

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def __repr__(self) -> str:
        status = "PASS" if self.success else "FAIL"
        return (
            f"TestResult({self.instance_id}, {status}, "
            f"{self.passed_tests}/{self.total_tests} passed)"
        )


class InstanceRunner:
    """Runs SWE-bench instances in Singularity containers."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize runner.

        Args:
            config: Configuration instance
        """
        from .config import get_config

        self.config = config or get_config()
        self.builder = SingularityBuilder(config)

    def prepare_container(
        self, instance_id: str, force_rebuild: bool = False
    ) -> Optional[Path]:
        """
        Prepare Singularity container for instance.

        Args:
            instance_id: Instance ID
            force_rebuild: Force rebuild of container

        Returns:
            Path to .sif file if successful, None otherwise
        """
        logger.info(f"Preparing container for {instance_id}...")

        result = self.builder.build_instance(
            instance_id=instance_id, force_rebuild=force_rebuild
        )

        if result.success:
            logger.info(f"Container ready: {result.sif_path}")
            return result.sif_path
        else:
            logger.error(f"Failed to prepare container: {result.error_message}")
            return None

    def run_command(
        self,
        sif_path: Path,
        command: str,
        working_dir: Optional[Path] = None,
        bind_paths: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a command in Singularity container.

        Args:
            sif_path: Path to .sif file
            command: Command to execute
            working_dir: Working directory to bind
            bind_paths: Additional paths to bind
            env_vars: Environment variables to set
            timeout: Timeout in seconds

        Returns:
            CompletedProcess result
        """
        # Build singularity exec command
        cmd = ["singularity", "exec"]

        # Add writable-tmpfs if configured
        if self.config.get("execution.use_writable_tmpfs", True):
            cmd.append("--writable-tmpfs")

        # Add bind paths
        all_bind_paths = bind_paths or []

        # Add configured bind paths
        configured_binds = self.config.get("execution.bind_paths", [])
        all_bind_paths.extend(configured_binds)

        # Add working directory
        if working_dir:
            all_bind_paths.append(f"{working_dir}:/workspace")

        for bind in all_bind_paths:
            cmd.extend(["--bind", bind])

        # Add environment variables
        all_env_vars = env_vars or {}

        # Add configured environment variables
        configured_env = self.config.get("execution.environment", {})
        all_env_vars.update(configured_env)

        for key, value in all_env_vars.items():
            cmd.extend(["--env", f"{key}={value}"])

        # Add container and command
        cmd.append(str(sif_path))
        cmd.extend(["/bin/bash", "-c", command])

        logger.debug(f"Executing: {' '.join(cmd)}")

        # Execute with timeout
        if timeout is None:
            timeout = self.config.get("execution.test_timeout", 300)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(working_dir) if working_dir else None,
            )
            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timeout after {timeout}s")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-1,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=f"Timeout after {timeout}s",
            )

    def run_pytest(
        self,
        sif_path: Path,
        test_dir: Path,
        test_files: Optional[List[str]] = None,
        pytest_args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> TestResult:
        """
        Run pytest in container.

        Args:
            sif_path: Path to .sif file
            test_dir: Test directory to bind and run in
            test_files: Specific test files to run (None = all)
            pytest_args: Additional pytest arguments
            timeout: Timeout in seconds

        Returns:
            TestResult with execution details
        """
        import time

        start_time = time.time()

        # Build pytest command
        pytest_cmd_parts = ["cd /workspace &&", "python", "-m", "pytest"]

        # Add pytest arguments
        args = pytest_args or []

        # Add JSON report for parsing results
        json_report = "/tmp/pytest_report.json"
        args.extend(["--json-report", f"--json-report-file={json_report}"])

        # Add configured pytest workers
        workers = self.config.get("execution.pytest_workers", 4)
        args.extend(["-n", str(workers)])

        # Add verbose output
        args.append("-v")

        # Add test files or directory
        if test_files:
            args.extend(test_files)
        else:
            args.append(".")

        pytest_cmd_parts.extend(args)
        pytest_cmd = " ".join(pytest_cmd_parts)

        # Run pytest
        logger.info(f"Running pytest in container: {pytest_cmd}")

        result = self.run_command(
            sif_path=sif_path,
            command=pytest_cmd,
            working_dir=test_dir,
            timeout=timeout,
        )

        execution_time = time.time() - start_time

        # Parse results
        # Try to extract test counts from output
        passed = 0
        failed = 0
        total = 0
        success = result.returncode == 0

        # Try to parse JSON report if available
        json_report_local = test_dir / "pytest_report.json"
        if json_report_local.exists():
            try:
                with open(json_report_local) as f:
                    report = json.load(f)
                    summary = report.get("summary", {})
                    passed = summary.get("passed", 0)
                    failed = summary.get("failed", 0)
                    total = summary.get("total", 0)
            except Exception as e:
                logger.warning(f"Failed to parse pytest JSON report: {e}")

        # Fallback: parse from stdout
        if total == 0 and result.stdout:
            import re

            # Look for pattern like "10 passed, 2 failed in 1.23s"
            match = re.search(
                r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+error", result.stdout
            )
            if match:
                for pattern in [
                    r"(\d+)\s+passed",
                    r"(\d+)\s+failed",
                    r"(\d+)\s+error",
                ]:
                    m = re.search(pattern, result.stdout)
                    if m:
                        count = int(m.group(1))
                        if "passed" in pattern:
                            passed = count
                        elif "failed" in pattern or "error" in pattern:
                            failed += count

                total = passed + failed

        return TestResult(
            instance_id="unknown",  # Set by caller
            success=success,
            passed_tests=passed,
            failed_tests=failed,
            total_tests=total,
            execution_time_seconds=execution_time,
            error_message=result.stderr if not success else None,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )

    def run_swebench_instance(
        self,
        instance_id: str,
        predictions_path: Optional[Path] = None,
        force_rebuild: bool = False,
        save_logs: bool = True,
    ) -> TestResult:
        """
        Run complete evaluation for a SWE-bench instance.

        This integrates with the existing evaluation pipeline to:
        1. Prepare the container
        2. Load instance data from SWE-bench dataset
        3. Apply patches
        4. Run tests
        5. Optionally run change-aware fuzzing

        Args:
            instance_id: SWE-bench instance ID
            predictions_path: Path to predictions/patch file
            force_rebuild: Force container rebuild
            save_logs: Save detailed logs

        Returns:
            TestResult with evaluation results
        """
        import time

        start_time = time.time()

        logger.info(f"Running SWE-bench instance: {instance_id}")

        # Step 1: Prepare container
        sif_path = self.prepare_container(instance_id, force_rebuild)
        if not sif_path:
            return TestResult(
                instance_id=instance_id,
                success=False,
                passed_tests=0,
                failed_tests=0,
                total_tests=0,
                execution_time_seconds=time.time() - start_time,
                error_message="Failed to prepare container",
                stdout=None,
                stderr=None,
                exit_code=-1,
            )

        # Step 2: Load instance from dataset
        # This would integrate with swebench_integration/dataset_loader.py
        # For now, we'll create a placeholder

        # TODO: Integrate with existing dataset loader
        logger.info(f"Loading instance data for {instance_id}")

        # Step 3: Run tests in container
        # This is a simplified version - full integration would use the
        # existing test_patch_singularity.py logic

        # For demonstration, we'll just run a simple command
        test_cmd = "python -m pytest --version"

        result = self.run_command(sif_path=sif_path, command=test_cmd, timeout=60)

        execution_time = time.time() - start_time

        # Create result
        test_result = TestResult(
            instance_id=instance_id,
            success=result.returncode == 0,
            passed_tests=0,
            failed_tests=0,
            total_tests=0,
            execution_time_seconds=execution_time,
            error_message=result.stderr if result.returncode != 0 else None,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )

        # Save logs if requested
        if save_logs:
            self._save_logs(instance_id, test_result)

        return test_result

    def _save_logs(self, instance_id: str, result: TestResult):
        """Save execution logs to file."""
        logs_dir = self.config.results_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / f"{instance_id}.json"

        try:
            with open(log_file, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            logger.debug(f"Saved logs to {log_file}")
        except Exception as e:
            logger.warning(f"Failed to save logs: {e}")

    def run_batch(
        self,
        instance_ids: List[str],
        predictions_path: Optional[Path] = None,
        force_rebuild: bool = False,
    ) -> Dict[str, TestResult]:
        """
        Run multiple instances sequentially.

        Args:
            instance_ids: List of instance IDs
            predictions_path: Path to predictions file
            force_rebuild: Force container rebuild

        Returns:
            Dictionary mapping instance_id to TestResult
        """
        results = {}

        for i, instance_id in enumerate(instance_ids, 1):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Running {i}/{len(instance_ids)}: {instance_id}")
            logger.info(f"{'=' * 60}\n")

            try:
                result = self.run_swebench_instance(
                    instance_id=instance_id,
                    predictions_path=predictions_path,
                    force_rebuild=force_rebuild,
                )
                results[instance_id] = result

                if result.success:
                    logger.info(f"✓ {instance_id}: SUCCESS")
                else:
                    logger.error(f"✗ {instance_id}: FAILED - {result.error_message}")

            except Exception as e:
                logger.error(f"Error running {instance_id}: {e}")
                results[instance_id] = TestResult(
                    instance_id=instance_id,
                    success=False,
                    passed_tests=0,
                    failed_tests=0,
                    total_tests=0,
                    execution_time_seconds=0,
                    error_message=str(e),
                    stdout=None,
                    stderr=None,
                    exit_code=-1,
                )

        # Summary
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Batch execution complete:")
        logger.info(f"  Total: {len(instance_ids)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"{'=' * 60}\n")

        return results
