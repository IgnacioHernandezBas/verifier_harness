"""
Docker Image Resolver for SWE-bench instances.

Resolves instance IDs to Docker image names, handles repository mapping,
and provides utilities for working with Docker images.
"""

import re
import logging
import subprocess
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class DockerImage:
    """Represents a Docker image reference."""

    registry: str
    repository: str
    tag: str

    @property
    def full_name(self) -> str:
        """Get full Docker image name."""
        if self.registry:
            return f"{self.registry}/{self.repository}:{self.tag}"
        return f"{self.repository}:{self.tag}"

    def __str__(self) -> str:
        return self.full_name


class DockerImageResolver:
    """Resolves SWE-bench instance IDs to Docker image names."""

    # Pattern to parse instance IDs
    # Format: <repo>__<repo_name>-<version>
    # Example: django__django-12345, pytest-dev__pytest-7490
    INSTANCE_PATTERN = re.compile(
        r"^(?P<org>[a-zA-Z0-9_-]+)__(?P<repo>[a-zA-Z0-9_.-]+)-(?P<version>\d+)$"
    )

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize resolver.

        Args:
            config: Configuration instance. If None, uses global config.
        """
        from .config import get_config

        self.config = config or get_config()

    def parse_instance_id(self, instance_id: str) -> Tuple[str, str, str]:
        """
        Parse instance ID into components.

        Args:
            instance_id: Instance ID (e.g., "django__django-12345")

        Returns:
            Tuple of (org, repo, version)

        Raises:
            ValueError: If instance ID is invalid
        """
        match = self.INSTANCE_PATTERN.match(instance_id)
        if not match:
            raise ValueError(f"Invalid instance ID format: {instance_id}")

        org = match.group("org")
        repo = match.group("repo")
        version = match.group("version")

        return org, repo, version

    def get_repo_full_name(self, instance_id: str) -> str:
        """
        Get full repository name from instance ID.

        Args:
            instance_id: Instance ID (e.g., "django__django-12345")

        Returns:
            Full repo name (e.g., "django/django")
        """
        org, repo, _ = self.parse_instance_id(instance_id)
        return f"{org}/{repo}"

    def get_repo_short_name(self, instance_id: str) -> str:
        """
        Get short repository name.

        Args:
            instance_id: Instance ID

        Returns:
            Short repo name (e.g., "django")
        """
        full_name = self.get_repo_full_name(instance_id)
        return self.config.get_repo_name(full_name)

    def resolve_docker_image(self, instance_id: str) -> List[DockerImage]:
        """
        Resolve instance ID to possible Docker image names.

        Tries multiple patterns in priority order based on configuration.

        Args:
            instance_id: Instance ID (e.g., "django__django-12345")

        Returns:
            List of possible DockerImage objects in priority order
        """
        org, repo, version = self.parse_instance_id(instance_id)
        full_repo = f"{org}/{repo}"

        # Get short repo name from mapping or use repo name
        short_repo = self.config.get_repo_name(full_repo)

        # Build list of possible images from patterns
        images = []
        patterns = self.config.docker_image_patterns

        for pattern in patterns:
            # Replace placeholders
            image_name = pattern.format(
                org=org,
                repo=short_repo,
                instance_id=instance_id,
                version=version,
                full_repo=full_repo.replace("/", "-"),
            )

            # Parse registry and repository
            if "://" in image_name:
                # Handle docker:// prefix
                image_name = image_name.replace("docker://", "")

            parts = image_name.split("/")
            if "." in parts[0] or ":" in parts[0]:
                # First part is a registry
                registry = parts[0]
                repo_parts = parts[1:]
            else:
                # No registry specified, use default
                registry = self.config.docker_registry
                repo_parts = parts

            # Split repository and tag
            repo_with_tag = "/".join(repo_parts)
            if ":" in repo_with_tag:
                repository, tag = repo_with_tag.rsplit(":", 1)
            else:
                repository = repo_with_tag
                tag = "latest"

            image = DockerImage(registry=registry, repository=repository, tag=tag)
            images.append(image)

        logger.debug(f"Resolved {instance_id} to {len(images)} possible images")
        return images

    def check_image_exists(self, image: DockerImage) -> bool:
        """
        Check if a Docker image exists in the registry.

        Args:
            image: DockerImage to check

        Returns:
            True if image exists, False otherwise
        """
        try:
            # Try to inspect the image remotely using docker manifest
            cmd = ["docker", "manifest", "inspect", image.full_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            exists = result.returncode == 0

            if exists:
                logger.debug(f"Image exists: {image.full_name}")
            else:
                logger.debug(f"Image not found: {image.full_name}")

            return exists

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking image: {image.full_name}")
            return False
        except FileNotFoundError:
            logger.warning("Docker command not found, assuming image exists")
            # If Docker is not available, we can't check, so assume it exists
            # and let Singularity handle the error
            return True
        except Exception as e:
            logger.warning(f"Error checking image {image.full_name}: {e}")
            return False

    def find_available_image(
        self, instance_id: str, check_existence: bool = True
    ) -> Optional[DockerImage]:
        """
        Find the first available Docker image for an instance.

        Args:
            instance_id: Instance ID
            check_existence: Whether to verify image exists in registry

        Returns:
            First available DockerImage, or None if none found
        """
        images = self.resolve_docker_image(instance_id)

        if not check_existence:
            # Return first image without checking
            return images[0] if images else None

        # Check each image in priority order
        for image in images:
            if self.check_image_exists(image):
                logger.info(f"Found Docker image for {instance_id}: {image.full_name}")
                return image

        logger.warning(f"No available Docker images found for {instance_id}")
        return None

    def get_docker_uri(self, instance_id: str) -> str:
        """
        Get Docker URI for instance ID.

        Args:
            instance_id: Instance ID

        Returns:
            Docker URI (e.g., "docker://aorwall/swe-bench-pytest:...")
        """
        image = self.find_available_image(instance_id, check_existence=False)
        if image:
            return f"docker://{image.full_name}"
        raise ValueError(f"Could not resolve Docker image for {instance_id}")

    def extract_instance_from_image(self, image_name: str) -> Optional[str]:
        """
        Extract instance ID from Docker image name (reverse operation).

        Args:
            image_name: Docker image name

        Returns:
            Instance ID if parseable, None otherwise
        """
        # Try to extract instance ID from tag
        # Common patterns:
        # - aorwall/swe-bench-pytest:pytest-dev__pytest-7490
        # - swebench/pytest:pytest-dev__pytest-7490

        if ":" in image_name:
            _, tag = image_name.rsplit(":", 1)
            # Check if tag matches instance pattern
            if self.INSTANCE_PATTERN.match(tag):
                return tag

        return None


def get_resolver(config: Optional[Config] = None) -> DockerImageResolver:
    """
    Get a DockerImageResolver instance.

    Args:
        config: Optional configuration

    Returns:
        DockerImageResolver instance
    """
    return DockerImageResolver(config)
