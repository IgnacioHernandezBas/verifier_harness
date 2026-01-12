"""
SWE-bench Test Executor using Singularity containers.

This module provides an executor that:
1. Converts SWE-bench Docker images to Singularity .sif files
2. Runs tests inside Singularity containers (no Podman needed)
3. Works on HPC systems with rootless container requirements

This replaces podman_executor.py for environments where Podman has UID/GID issues.
"""

import subprocess
import tempfile
import shutil
import json
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from swebench_singularity.singularity_builder import SingularityBuilder, BuildResult
from swebench_singularity.docker_resolver import DockerImageResolver, DockerImage
from swebench_singularity.instance_runner import InstanceRunner
from swebench_singularity.config import Config, get_config


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


class SingularitySWEBenchExecutor:
    """
    Execute SWE-bench tests in Singularity containers.

    This executor replaces PodmanTestExecutor and uses the existing
    swebench_singularity infrastructure to avoid Podman UID/GID issues.
    """

    def __init__(
        self,
        scratch_dir: str = "/scratch0/ihbas",
        timeout: int = 300,
        enable_coverage: bool = True,
        config: Optional[Config] = None,
        auto_cleanup: bool = True
    ):
        """
        Initialize the Singularity executor.

        Args:
            scratch_dir: Local scratch directory for operations
            timeout: Default timeout for test execution (seconds)
            enable_coverage: Whether to collect coverage data
            config: Optional Singularity config (will create default if not provided)
            auto_cleanup: Whether to automatically clean cache before builds (default: True)
        """
        self.scratch_dir = Path(scratch_dir)
        self.timeout = timeout
        self.enable_coverage = enable_coverage
        self.auto_cleanup = auto_cleanup

        # Verify scratch directory exists
        if not self.scratch_dir.exists():
            raise RuntimeError(
                f"Scratch directory {scratch_dir} not found. "
                "This executor requires local storage (not NFS)."
            )

        # Initialize Singularity infrastructure
        if config is None:
            # Create config with scratch-based directories
            config = self._create_scratch_config()

        self.config = config
        self.builder = SingularityBuilder(config)
        self.resolver = DockerImageResolver(config)

    def _create_scratch_config(self) -> Config:
        """Create configuration using scratch directories."""
        config = get_config()

        # Override cache directories to use scratch
        cache_base = self.scratch_dir / "singularity_cache"

        # Use task-specific temp directory to avoid parallel job conflicts
        # This prevents race conditions when multiple jobs run on same node
        task_id = os.environ.get('SLURM_ARRAY_TASK_ID', str(os.getpid()))

        # Shared locations (reused across tasks)
        config.set("singularity.cache_dir", str(cache_base / "images"))

        # Task-isolated locations (per-job to avoid conflicts)
        config.set("singularity.tmp_dir", str(cache_base / "tmp" / f"task_{task_id}"))
        config.set("singularity.cache_internal_dir", str(cache_base / "internal" / f"task_{task_id}"))

        # Ensure directories exist
        for key in ["singularity.cache_dir", "singularity.tmp_dir", "singularity.cache_internal_dir"]:
            Path(config.get(key)).mkdir(parents=True, exist_ok=True)

        return config

    def _cleanup_cache(self, aggressive: bool = False) -> None:
        """
        Clean up Singularity cache to free disk space.

        Only cleans THIS task's directories to avoid interfering with parallel jobs.

        Args:
            aggressive: If True, remove all cache. If False, only remove tmp files.
        """
        # Clean only this task's tmp directory (safe for parallel execution)
        tmp_dir = Path(self.config.get("singularity.tmp_dir"))
        if tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                tmp_dir.mkdir(parents=True, exist_ok=True)
                print(f"  Cleaned task tmp cache: {tmp_dir}")
            except Exception as e:
                print(f"  Warning: Failed to clean tmp cache: {e}")

        # Clean this task's internal cache if aggressive mode
        if aggressive:
            internal_dir = Path(self.config.get("singularity.cache_internal_dir"))
            if internal_dir.exists():
                try:
                    shutil.rmtree(internal_dir, ignore_errors=True)
                    internal_dir.mkdir(parents=True, exist_ok=True)
                    print(f"  Cleaned task internal cache: {internal_dir}")
                except Exception as e:
                    print(f"  Warning: Failed to clean internal cache: {e}")

    def get_docker_image(self, instance_id: str) -> str:
        """
        Convert instance ID to Docker image name.

        Args:
            instance_id: SWE-bench instance ID (e.g., 'django__django-12345')

        Returns:
            Docker image name
        """
        parts = instance_id.split('__')
        if len(parts) != 2:
            raise ValueError(f"Invalid instance ID format: {instance_id}")

        org = parts[0]
        rest = parts[1]
        repo_and_num = rest.replace('__', '_')
        return f"docker.io/swebench/sweb.eval.x86_64.{org}_1776_{repo_and_num}:latest"

    def _build_sif_for_instance(self, instance_id: str) -> Optional[Path]:
        """
        Build or retrieve cached Singularity .sif file for instance.

        Args:
            instance_id: SWE-bench instance ID

        Returns:
            Path to .sif file if successful, None otherwise
        """
        try:
            # Clean cache before building to ensure sufficient disk space
            if self.auto_cleanup:
                self._cleanup_cache(aggressive=False)

            # Use the SingularityBuilder to convert Docker -> .sif
            result = self.builder.build_instance(instance_id, force_rebuild=False)

            if result.success:
                return result.sif_path
            else:
                print(f"  Error building .sif: {result.error_message}")
                return None

        except Exception as e:
            print(f"  Error in _build_sif_for_instance: {e}")
            return None

    def run_swebench_tests(
        self,
        instance_id: str,
        patch_diff: str,
        eval_script_path: Path,
        output_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """
        Run official SWE-bench tests for an instance.

        Args:
            instance_id: SWE-bench instance ID
            patch_diff: The code patch to apply (unified diff format)
            eval_script_path: Path to the eval.sh file
            output_dir: Directory to store outputs (optional)

        Returns:
            ExecutionResult with test outcome
        """
        start_time = time.time()

        # Build/get .sif file
        sif_path = self._build_sif_for_instance(instance_id)
        if not sif_path:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                test_output="",
                error="Failed to build Singularity image",
                execution_time=time.time() - start_time
            )

        # Setup directories
        if output_dir is None:
            output_dir = self.scratch_dir / "swebench_results" / instance_id
        output_dir.mkdir(parents=True, exist_ok=True)

        patch_dir = self.scratch_dir / "patches" / instance_id
        patch_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy eval.sh and patch to scratch
            shutil.copy(eval_script_path, patch_dir / "eval.sh")
            (patch_dir / "patch.diff").write_text(patch_diff)

            # Build the container script
            container_script = self._build_swebench_test_script()

            # Run in Singularity
            result = self._run_singularity_command(
                sif_path=sif_path,
                command=container_script,
                bind_paths={
                    str(patch_dir): "/patch:ro",
                    str(output_dir): "/output"
                },
                workdir="/testbed"
            )

            # Read outputs
            test_output_file = output_dir / "test_output.txt"
            test_output = test_output_file.read_text() if test_output_file.exists() else ""

            exit_code_file = output_dir / "exit_code.txt"
            exit_code = result.returncode
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

    def run_custom_tests(
        self,
        instance_id: str,
        patch_diff: str,
        test_code: str,
        test_type: TestType = TestType.CUSTOM,
        output_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """
        Run custom tests (fuzzing, invariance, etc.) in Singularity container.

        Args:
            instance_id: SWE-bench instance ID
            patch_diff: The code patch to apply
            test_code: Python test code to execute
            test_type: Type of test being run
            output_dir: Directory to store outputs

        Returns:
            ExecutionResult with test outcome
        """
        start_time = time.time()

        # Build/get .sif file
        sif_path = self._build_sif_for_instance(instance_id)
        if not sif_path:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                test_output="",
                error="Failed to build Singularity image",
                execution_time=time.time() - start_time
            )

        # Setup directories
        if output_dir is None:
            output_dir = self.scratch_dir / "swebench_results" / instance_id / test_type.value
        output_dir.mkdir(parents=True, exist_ok=True)

        patch_dir = self.scratch_dir / "patches" / instance_id
        patch_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write patch and test code
            (patch_dir / "patch.diff").write_text(patch_diff)
            (patch_dir / "custom_tests.py").write_text(test_code)

            # Build the container script for custom tests
            container_script = self._build_custom_test_script(
                enable_coverage=self.enable_coverage
            )

            # Run in Singularity
            result = self._run_singularity_command(
                sif_path=sif_path,
                command=container_script,
                bind_paths={
                    str(patch_dir): "/patch:ro",
                    str(output_dir): "/output"
                },
                workdir="/testbed"
            )

            # Read outputs
            test_output_file = output_dir / "test_output.txt"
            test_output = test_output_file.read_text() if test_output_file.exists() else ""

            exit_code_file = output_dir / "exit_code.txt"
            exit_code = result.returncode
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

    def _run_singularity_command(
        self,
        sif_path: Path,
        command: str,
        bind_paths: Dict[str, str],
        workdir: str = "/workspace",
        env_vars: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a command in Singularity container.

        Args:
            sif_path: Path to .sif file
            command: Shell command to execute
            bind_paths: Dict mapping host_path -> container_path
            workdir: Working directory in container
            env_vars: Environment variables to set

        Returns:
            CompletedProcess result
        """
        cmd = ["singularity", "exec", "--writable-tmpfs"]

        # Add bind mounts
        for host_path, container_path in bind_paths.items():
            cmd.extend(["--bind", f"{host_path}:{container_path}"])

        # Add environment variables
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["--env", f"{key}={value}"])

        # Add working directory
        cmd.extend(["--pwd", workdir])

        # Add image and command
        cmd.append(str(sif_path))
        cmd.extend(["/bin/bash", "-c", command])

        # Execute
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )

        return result

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
        sed "1d;$d" | git apply -v >> /output/patch.log 2>&1 || true

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
