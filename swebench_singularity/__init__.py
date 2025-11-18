"""
SWE-bench Singularity Runner

A dynamic container management system for running SWE-bench evaluations
with Singularity containers. Handles Docker image fetching, conversion,
caching, and test execution.
"""

__version__ = "1.0.0"
__author__ = "SWE-bench Verifier Team"

from .config import Config
from .docker_resolver import DockerImageResolver
from .singularity_builder import SingularityBuilder
from .cache_manager import CacheManager
from .instance_runner import InstanceRunner

__all__ = [
    "Config",
    "DockerImageResolver",
    "SingularityBuilder",
    "CacheManager",
    "InstanceRunner",
]
