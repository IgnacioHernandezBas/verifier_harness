"""
Singularity Builder for SWE-bench instances.

Handles Docker to Singularity conversion, manages build process,
integrates with cache manager, and provides retry logic.
"""

import os
import subprocess
import logging
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config import Config
from .docker_resolver import DockerImageResolver, DockerImage
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result of a Singularity build operation."""

    success: bool
    sif_path: Optional[Path]
    error_message: Optional[str]
    build_time_seconds: float
    from_cache: bool

    def __repr__(self) -> str:
        status = "SUCCESS (cached)" if self.from_cache else "SUCCESS" if self.success else "FAILED"
        return f"BuildResult({status}, {self.build_time_seconds:.1f}s)"


class SingularityBuilder:
    """Builds Singularity images from Docker images."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize builder.

        Args:
            config: Configuration instance
        """
        from .config import get_config

        self.config = config or get_config()
        self.resolver = DockerImageResolver(config)
        self.cache = CacheManager(config)

        # Setup environment for Singularity
        self._setup_environment()

    def _setup_environment(self):
        """Setup environment variables for Singularity."""
        # Set temporary directory
        tmp_dir = str(self.config.singularity_tmp_dir)
        os.environ["SINGULARITY_TMPDIR"] = tmp_dir
        os.environ["TMPDIR"] = tmp_dir

        # Set cache directory
        cache_dir = str(self.config.singularity_cache_internal_dir)
        os.environ["SINGULARITY_CACHEDIR"] = cache_dir

        logger.debug(f"Singularity environment: TMPDIR={tmp_dir}, CACHEDIR={cache_dir}")

    def check_docker_available(self) -> bool:
        """
        Check if Docker is available and responding.

        Returns:
            True if docker command is available and working
        """
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.debug("Docker is available")
                return True
            logger.debug(f"Docker not responding: {result.stderr}")
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.debug("Docker command not found or not responding")
            return False

    def docker_pull(self, docker_image: DockerImage, timeout: int = 600) -> bool:
        """
        Pull Docker image using docker pull command.

        This leverages Docker's authentication which is typically already
        configured (via docker login or credential helpers).

        Args:
            docker_image: Docker image to pull
            timeout: Pull timeout in seconds

        Returns:
            True if pull succeeded
        """
        full_name = docker_image.full_name
        logger.info(f"Pulling Docker image: {full_name}")

        try:
            result = subprocess.run(
                ["docker", "pull", full_name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                logger.info(f"Successfully pulled: {full_name}")
                return True
            else:
                logger.error(f"Docker pull failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Docker pull timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Docker pull error: {e}")
            return False

    def build_from_docker_daemon(
        self,
        docker_image: DockerImage,
        output_path: Path,
        force: bool = False,
        use_fakeroot: Optional[bool] = None,
    ) -> BuildResult:
        """
        Build Singularity image from local Docker daemon.

        This method pulls the Docker image first (using Docker's auth),
        then converts it to Singularity from the local daemon.

        Args:
            docker_image: Docker image to convert
            output_path: Output path for .sif file
            force: Force rebuild even if output exists
            use_fakeroot: Use --fakeroot flag (None = use config default)

        Returns:
            BuildResult with operation details
        """
        start_time = time.time()

        # Check if output already exists
        if output_path.exists() and not force:
            logger.info(f"Output file already exists: {output_path}")
            return BuildResult(
                success=True,
                sif_path=output_path,
                error_message=None,
                build_time_seconds=time.time() - start_time,
                from_cache=True,
            )

        # Step 1: Pull Docker image
        pull_timeout = self.config.get("docker.pull_timeout", 600)
        if not self.docker_pull(docker_image, timeout=pull_timeout):
            error_msg = f"Failed to pull Docker image: {docker_image.full_name}"
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=error_msg,
                build_time_seconds=time.time() - start_time,
                from_cache=False,
            )

        # Step 2: Convert from Docker daemon
        # Prepare build directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build command using docker-daemon:// URI
        docker_uri = f"docker-daemon://{docker_image.full_name}"
        cmd = ["singularity", "build"]

        # Add fakeroot flag if configured
        if use_fakeroot is None:
            use_fakeroot = self.config.get("singularity.use_fakeroot", True)

        if use_fakeroot:
            cmd.append("--fakeroot")

        cmd.extend([str(output_path), docker_uri])

        logger.info(f"Building Singularity image from daemon: {' '.join(cmd)}")

        try:
            # Run build with timeout
            timeout = self.config.get("singularity.build_timeout", 1800)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy(),
            )

            build_time = time.time() - start_time

            if result.returncode == 0:
                # Verify output file exists and has content
                if output_path.exists() and output_path.stat().st_size > 0:
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    logger.info(
                        f"Successfully built {output_path.name} ({size_mb:.1f} MB) in {build_time:.1f}s"
                    )

                    return BuildResult(
                        success=True,
                        sif_path=output_path,
                        error_message=None,
                        build_time_seconds=build_time,
                        from_cache=False,
                    )
                else:
                    error_msg = "Build succeeded but output file is missing or empty"
                    logger.error(error_msg)
                    return BuildResult(
                        success=False,
                        sif_path=None,
                        error_message=error_msg,
                        build_time_seconds=build_time,
                        from_cache=False,
                    )
            else:
                error_msg = f"Build failed: {result.stderr}"

                # Check for authentication errors and provide helpful message
                if "UNAUTHORIZED" in result.stderr or "authentication required" in result.stderr:
                    error_msg += (
                        "\n\nDocker Hub authentication required. Please either:\n"
                        "  1. Run 'docker login' to authenticate with Docker Hub, or\n"
                        "  2. Set SINGULARITY_DOCKER_USERNAME and SINGULARITY_DOCKER_PASSWORD environment variables\n"
                        "Note: Docker authentication is recommended as it provides better reliability."
                    )

                logger.error(error_msg)
                return BuildResult(
                    success=False,
                    sif_path=None,
                    error_message=error_msg,
                    build_time_seconds=build_time,
                    from_cache=False,
                )

        except subprocess.TimeoutExpired:
            build_time = time.time() - start_time
            error_msg = f"Build timeout after {timeout}s"
            logger.error(error_msg)
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=error_msg,
                build_time_seconds=build_time,
                from_cache=False,
            )

        except Exception as e:
            build_time = time.time() - start_time
            error_msg = f"Build error: {str(e)}"
            logger.error(error_msg)
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=error_msg,
                build_time_seconds=build_time,
                from_cache=False,
            )

    def check_singularity_available(self) -> bool:
        """
        Check if Singularity is available.

        Returns:
            True if singularity command is available
        """
        try:
            result = subprocess.run(
                ["singularity", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"Singularity available: {version}")
                return True
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("Singularity command not found or not responding")
            return False

    def build_from_docker(
        self,
        docker_image: DockerImage,
        output_path: Path,
        force: bool = False,
        use_fakeroot: Optional[bool] = None,
    ) -> BuildResult:
        """
        Build Singularity image from Docker image.

        Args:
            docker_image: Docker image to convert
            output_path: Output path for .sif file
            force: Force rebuild even if output exists
            use_fakeroot: Use --fakeroot flag (None = use config default)

        Returns:
            BuildResult with operation details
        """
        start_time = time.time()

        # Check if output already exists
        if output_path.exists() and not force:
            logger.info(f"Output file already exists: {output_path}")
            return BuildResult(
                success=True,
                sif_path=output_path,
                error_message=None,
                build_time_seconds=time.time() - start_time,
                from_cache=True,
            )

        # Prepare build directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build command
        docker_uri = f"docker://{docker_image.full_name}"
        cmd = ["singularity", "build"]

        # Add fakeroot flag if configured
        if use_fakeroot is None:
            use_fakeroot = self.config.get("singularity.use_fakeroot", True)

        if use_fakeroot:
            cmd.append("--fakeroot")

        cmd.extend([str(output_path), docker_uri])

        logger.info(f"Building Singularity image: {' '.join(cmd)}")

        try:
            # Run build with timeout
            timeout = self.config.get("singularity.build_timeout", 1800)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy(),
            )

            build_time = time.time() - start_time

            if result.returncode == 0:
                # Verify output file exists and has content
                if output_path.exists() and output_path.stat().st_size > 0:
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    logger.info(
                        f"Successfully built {output_path.name} ({size_mb:.1f} MB) in {build_time:.1f}s"
                    )

                    return BuildResult(
                        success=True,
                        sif_path=output_path,
                        error_message=None,
                        build_time_seconds=build_time,
                        from_cache=False,
                    )
                else:
                    error_msg = "Build succeeded but output file is missing or empty"
                    logger.error(error_msg)
                    return BuildResult(
                        success=False,
                        sif_path=None,
                        error_message=error_msg,
                        build_time_seconds=build_time,
                        from_cache=False,
                    )
            else:
                error_msg = f"Build failed: {result.stderr}"

                # Check for authentication errors and provide helpful message
                if "UNAUTHORIZED" in result.stderr or "authentication required" in result.stderr:
                    error_msg += (
                        "\n\nDocker Hub authentication required. Please either:\n"
                        "  1. Run 'docker login' to authenticate with Docker Hub, or\n"
                        "  2. Set SINGULARITY_DOCKER_USERNAME and SINGULARITY_DOCKER_PASSWORD environment variables\n"
                        "Note: Docker authentication is recommended as it provides better reliability."
                    )

                logger.error(error_msg)
                return BuildResult(
                    success=False,
                    sif_path=None,
                    error_message=error_msg,
                    build_time_seconds=build_time,
                    from_cache=False,
                )

        except subprocess.TimeoutExpired:
            build_time = time.time() - start_time
            error_msg = f"Build timeout after {timeout}s"
            logger.error(error_msg)
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=error_msg,
                build_time_seconds=build_time,
                from_cache=False,
            )

        except Exception as e:
            build_time = time.time() - start_time
            error_msg = f"Build error: {str(e)}"
            logger.error(error_msg)
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=error_msg,
                build_time_seconds=build_time,
                from_cache=False,
            )

    def build_instance(
        self,
        instance_id: str,
        force_rebuild: bool = False,
        check_docker_exists: bool = True,
    ) -> BuildResult:
        """
        Build Singularity image for a SWE-bench instance.

        This is the main entry point that handles:
        - Cache checking
        - Docker image resolution
        - Building with retries
        - Cache storage

        Args:
            instance_id: SWE-bench instance ID
            force_rebuild: Force rebuild even if cached
            check_docker_exists: Check if Docker image exists before building

        Returns:
            BuildResult with operation details
        """
        start_time = time.time()

        # Extract repository name for cache organization
        try:
            repo_name = self.resolver.get_repo_short_name(instance_id)
        except ValueError as e:
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=str(e),
                build_time_seconds=0,
                from_cache=False,
            )

        # Check cache first (unless force rebuild)
        if not force_rebuild:
            cached_path = self.cache.get(instance_id, repo_name)
            if cached_path:
                logger.info(f"Using cached image for {instance_id}: {cached_path}")
                return BuildResult(
                    success=True,
                    sif_path=cached_path,
                    error_message=None,
                    build_time_seconds=time.time() - start_time,
                    from_cache=True,
                )

        # Resolve Docker image
        logger.info(f"Resolving Docker image for {instance_id}...")
        docker_image = self.resolver.find_available_image(
            instance_id, check_existence=check_docker_exists
        )

        if not docker_image:
            error_msg = f"No available Docker image found for {instance_id}"
            logger.error(error_msg)
            return BuildResult(
                success=False,
                sif_path=None,
                error_message=error_msg,
                build_time_seconds=time.time() - start_time,
                from_cache=False,
            )

        # Get target path (temporary location)
        temp_dir = self.config.singularity_tmp_dir
        temp_sif = temp_dir / f"{instance_id}.sif"

        # Check if Docker is available for authentication
        use_docker_daemon = self.check_docker_available()
        if use_docker_daemon:
            logger.info("Docker is available, using Docker daemon for authenticated pull")
        else:
            logger.info("Docker not available, using direct Singularity build")

        # Build with retries
        max_retries = self.config.get("docker.max_retries", 3)
        retry_delay = self.config.get("docker.retry_delay", 5)

        last_result = None
        for attempt in range(max_retries):
            if attempt > 0:
                logger.info(
                    f"Retry attempt {attempt + 1}/{max_retries} for {instance_id}"
                )
                time.sleep(retry_delay * attempt)  # Exponential backoff

            # Use Docker daemon if available (handles authentication better)
            if use_docker_daemon:
                result = self.build_from_docker_daemon(
                    docker_image=docker_image,
                    output_path=temp_sif,
                    force=True,  # Always rebuild in temp location
                )
            else:
                result = self.build_from_docker(
                    docker_image=docker_image,
                    output_path=temp_sif,
                    force=True,  # Always rebuild in temp location
                )

            last_result = result

            if result.success:
                # Move to cache
                cached_path = self.cache.put(instance_id, temp_sif, repo_name)

                # Clean up temp file if different from cache
                if temp_sif != cached_path and temp_sif.exists():
                    temp_sif.unlink()

                return BuildResult(
                    success=True,
                    sif_path=cached_path,
                    error_message=None,
                    build_time_seconds=time.time() - start_time,
                    from_cache=False,
                )

        # All retries failed
        logger.error(
            f"Failed to build {instance_id} after {max_retries} attempts"
        )
        return last_result or BuildResult(
            success=False,
            sif_path=None,
            error_message="Build failed after all retries",
            build_time_seconds=time.time() - start_time,
            from_cache=False,
        )

    def build_batch(
        self, instance_ids: list[str], force_rebuild: bool = False
    ) -> dict[str, BuildResult]:
        """
        Build multiple instances sequentially.

        Args:
            instance_ids: List of instance IDs to build
            force_rebuild: Force rebuild for all instances

        Returns:
            Dictionary mapping instance_id to BuildResult
        """
        results = {}

        for i, instance_id in enumerate(instance_ids, 1):
            logger.info(f"Building {i}/{len(instance_ids)}: {instance_id}")

            try:
                result = self.build_instance(instance_id, force_rebuild)
                results[instance_id] = result

                if result.success:
                    logger.info(f"✓ {instance_id}: {result}")
                else:
                    logger.error(f"✗ {instance_id}: {result.error_message}")

            except Exception as e:
                logger.error(f"Error building {instance_id}: {e}")
                results[instance_id] = BuildResult(
                    success=False,
                    sif_path=None,
                    error_message=str(e),
                    build_time_seconds=0,
                    from_cache=False,
                )

        # Summary
        successful = sum(1 for r in results.values() if r.success)
        cached = sum(1 for r in results.values() if r.from_cache)
        failed = len(results) - successful

        logger.info(
            f"\nBatch build complete: {successful}/{len(instance_ids)} successful "
            f"({cached} from cache, {failed} failed)"
        )

        return results

    def get_image_path(self, instance_id: str) -> Optional[Path]:
        """
        Get path to Singularity image for instance (if exists in cache).

        Args:
            instance_id: Instance ID

        Returns:
            Path to .sif file if cached, None otherwise
        """
        try:
            repo_name = self.resolver.get_repo_short_name(instance_id)
            return self.cache.get(instance_id, repo_name)
        except ValueError:
            return None
