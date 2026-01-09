"""
Dynamic Atheris Installation for SWE-bench Instance Containers.

This module handles installing Atheris into existing SWE-bench containers
to enable coverage-guided fuzzing while maintaining library compatibility.

ARCHITECTURE:
1. Use existing SWE-bench instance containers (correct Python version + dependencies)
2. Check if Atheris is already installed in the container
3. If not, install it using pip within the container
4. Cache Atheris-enabled containers for reuse
5. Fall back to Hypothesis if Atheris installation fails
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AtherisInstallResult:
    """Result of Atheris installation attempt."""
    success: bool
    atheris_version: Optional[str]
    python_version: str
    container_path: str
    error_message: Optional[str] = None
    fallback_to_hypothesis: bool = False


class AtherisInstaller:
    """Manages Atheris installation in SWE-bench containers."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the Atheris installer.

        Args:
            cache_dir: Directory to cache Atheris installation status.
                      Defaults to ~/.cache/verifier/atheris
        """
        self.cache_dir = cache_dir or Path.home() / ".cache" / "verifier" / "atheris"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def check_atheris_installed(self, container_image: str) -> Tuple[bool, Optional[str]]:
        """
        Check if Atheris is installed in the container.

        Args:
            container_image: Path to Singularity/Podman container image

        Returns:
            Tuple of (is_installed, version_string)
        """
        try:
            result = subprocess.run(
                ["singularity", "exec", container_image,
                 "python", "-c", "import atheris; print(atheris.__file__)"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Atheris is installed
                version_result = subprocess.run(
                    ["singularity", "exec", container_image,
                     "python", "-c", "import atheris; import pkg_resources; print(pkg_resources.get_distribution('atheris').version)"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                version = version_result.stdout.strip() if version_result.returncode == 0 else "unknown"
                logger.info(f"Atheris {version} already installed in {container_image}")
                return True, version
            else:
                logger.info(f"Atheris not found in {container_image}")
                return False, None

        except Exception as e:
            logger.warning(f"Error checking Atheris installation: {e}")
            return False, None

    def get_python_version(self, container_image: str) -> Optional[str]:
        """Get Python version from container."""
        try:
            result = subprocess.run(
                ["singularity", "exec", container_image, "python", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                return version
            return None
        except Exception as e:
            logger.error(f"Error getting Python version: {e}")
            return None

    def install_atheris(self, container_image: str,
                       writable: bool = True) -> AtherisInstallResult:
        """
        Install Atheris in the container.

        Args:
            container_image: Path to container image
            writable: Whether the container is writable (sandbox mode allows temp writes)

        Returns:
            AtherisInstallResult with installation status
        """
        python_version = self.get_python_version(container_image) or "unknown"

        # Check if already installed
        is_installed, version = self.check_atheris_installed(container_image)
        if is_installed:
            return AtherisInstallResult(
                success=True,
                atheris_version=version,
                python_version=python_version,
                container_path=container_image
            )

        # Try to install Atheris
        logger.info(f"Installing Atheris in {container_image}...")

        try:
            # Method 1: Try installing to user site-packages (works in sandbox mode)
            result = subprocess.run(
                ["singularity", "exec", "--writable-tmpfs", container_image,
                 "python", "-m", "pip", "install", "--user", "atheris"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for installation
            )

            if result.returncode == 0:
                # Verify installation
                is_installed, version = self.check_atheris_installed(container_image)
                if is_installed:
                    logger.info(f"Successfully installed Atheris {version}")
                    return AtherisInstallResult(
                        success=True,
                        atheris_version=version,
                        python_version=python_version,
                        container_path=container_image
                    )

            # Method 2: Try installing to temp location with PYTHONPATH
            logger.warning("User install failed, trying temp install...")
            temp_install_dir = self.cache_dir / f"atheris_install_{hash(container_image) % 100000}"
            temp_install_dir.mkdir(exist_ok=True)

            result = subprocess.run(
                ["singularity", "exec",
                 "-B", f"{temp_install_dir}:/tmp/atheris_lib",
                 container_image,
                 "python", "-m", "pip", "install", "--target=/tmp/atheris_lib", "atheris"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info("Atheris installed to temp directory")
                return AtherisInstallResult(
                    success=True,
                    atheris_version="temp-install",
                    python_version=python_version,
                    container_path=container_image,
                    error_message="Using temp install, requires PYTHONPATH=/tmp/atheris_lib"
                )

            # Installation failed - fall back to Hypothesis
            error_msg = result.stderr if result.stderr else "Unknown error"
            logger.error(f"Atheris installation failed: {error_msg}")
            logger.info("Falling back to Hypothesis for fuzzing")

            return AtherisInstallResult(
                success=False,
                atheris_version=None,
                python_version=python_version,
                container_path=container_image,
                error_message=error_msg,
                fallback_to_hypothesis=True
            )

        except subprocess.TimeoutExpired:
            logger.error("Atheris installation timed out")
            return AtherisInstallResult(
                success=False,
                atheris_version=None,
                python_version=python_version,
                container_path=container_image,
                error_message="Installation timeout",
                fallback_to_hypothesis=True
            )
        except Exception as e:
            logger.error(f"Atheris installation error: {e}")
            return AtherisInstallResult(
                success=False,
                atheris_version=None,
                python_version=python_version,
                container_path=container_image,
                error_message=str(e),
                fallback_to_hypothesis=True
            )

    def prepare_container_for_fuzzing(self,
                                      instance_id: str,
                                      container_image: str) -> AtherisInstallResult:
        """
        Prepare a SWE-bench container for Atheris fuzzing.

        Args:
            instance_id: SWE-bench instance identifier
            container_image: Path to the instance's container

        Returns:
            AtherisInstallResult with preparation status
        """
        logger.info(f"Preparing container for instance {instance_id}")

        # Check cache
        cache_file = self.cache_dir / f"{instance_id}.status"
        if cache_file.exists():
            logger.info(f"Using cached Atheris status for {instance_id}")

        # Install or verify Atheris
        result = self.install_atheris(container_image)

        # Update cache
        if result.success:
            cache_file.write_text(f"{result.atheris_version}\n{result.python_version}")

        return result


def get_container_for_instance(instance_id: str) -> Optional[str]:
    """
    Get the container image path for a SWE-bench instance.

    Args:
        instance_id: SWE-bench instance ID (e.g., "django__django-12345")

    Returns:
        Path to container image, or None if not found
    """
    # Check common container locations
    container_paths = [
        f"/fs/nexus-scratch/ihbas/.containers/singularity/{instance_id}.sif",
        "/fs/nexus-scratch/ihbas/.containers/singularity/verifier-swebench.sif",
        f"/fs/nexus-scratch/ihbas/.containers/singularity/{instance_id.split('__')[0]}.sif",
    ]

    for path in container_paths:
        if os.path.exists(path):
            return path

    return None
