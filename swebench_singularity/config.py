"""
Configuration management for SWE-bench Singularity Runner.

Loads and validates configuration from YAML file, provides
convenient access to settings with fallback defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for SWE-bench Singularity Runner."""

    # Default configuration
    DEFAULTS = {
        "docker": {
            "registry": "docker.io",
            "image_patterns": [
                "swebench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest",
                "ghcr.io/swe-bench/sweb.eval.x86_64.{org}_1776_{repo}-{version}:latest",
                "aorwall/swe-bench-{repo}:{instance_id}",
                "swebench/{repo}:{instance_id}",
            ],
            "pull_timeout": 600,
            "max_retries": 3,
            "retry_delay": 5,
        },
        "singularity": {
            "cache_dir": os.path.expanduser("~/.cache/swebench_singularity"),
            "tmp_dir": "/tmp/singularity_build",
            "cache_internal_dir": os.path.expanduser("~/.singularity/cache"),
            "build_timeout": 1800,
            "use_fakeroot": True,
            "cleanup_after_days": 30,
            "max_cache_size_gb": 100,
            "sif_naming": "{instance_id}.sif",
        },
        "execution": {
            "test_timeout": 300,
            "pytest_workers": 4,
            "bind_paths": [],
            "environment": {
                "PYTHONPATH": "/workspace",
            },
            "use_writable_tmpfs": True,
        },
        "logging": {
            "level": "INFO",
            "file": None,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "console": True,
        },
        "cache": {
            "enabled": True,
            "check_updates": False,
            "organize_by_repo": True,
            "create_symlinks": False,
        },
        "parallel": {
            "max_workers": 10,
            "chunk_size": 5,
            "fail_fast": False,
        },
        "integration": {
            "enable_fuzzing": True,
            "enable_static_analysis": True,
            "results_dir": "results/swebench_singularity",
            "save_instance_logs": True,
        },
        "repo_mapping": {},
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML configuration file.
                        If None, uses default config location.
        """
        self._config = self._load_config(config_path)
        self._setup_logging()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML file with fallback to defaults."""
        # Determine config file path
        if config_path is None:
            # Try standard locations
            possible_paths = [
                Path(__file__).parent.parent / "config" / "swebench_config.yaml",
                Path.home() / ".config" / "swebench_singularity" / "config.yaml",
                Path("config") / "swebench_config.yaml",
            ]
            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break

        # Load config file if it exists
        config = {}
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from: {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                logger.warning("Using default configuration")
        else:
            logger.info("No config file found, using defaults")

        # Merge with defaults (deep merge)
        return self._deep_merge(self.DEFAULTS.copy(), config)

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _setup_logging(self):
        """Setup logging based on configuration."""
        log_config = self._config.get("logging", {})

        # Configure root logger
        level = getattr(logging, log_config.get("level", "INFO"))
        format_str = log_config.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create handlers
        handlers = []

        # Console handler
        if log_config.get("console", True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(format_str))
            handlers.append(console_handler)

        # File handler
        log_file = log_config.get("file")
        if log_file:
            log_file = os.path.expanduser(log_file)
            log_dir = os.path.dirname(log_file)
            if log_dir:  # Only create directory if path contains a directory
                os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(format_str))
            handlers.append(file_handler)

        # Configure logger
        logging.basicConfig(level=level, handlers=handlers, force=True)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "docker.registry")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "docker.registry")
            value: Value to set
        """
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    @property
    def docker_registry(self) -> str:
        """Get Docker registry URL."""
        return self.get("docker.registry", "docker.io")

    @property
    def docker_image_patterns(self) -> List[str]:
        """Get Docker image naming patterns."""
        return self.get("docker.image_patterns", [])

    @property
    def singularity_cache_dir(self) -> Path:
        """Get Singularity cache directory."""
        cache_dir = Path(self.get("singularity.cache_dir"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @property
    def singularity_tmp_dir(self) -> Path:
        """Get Singularity temporary directory."""
        tmp_dir = Path(self.get("singularity.tmp_dir"))
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir

    @property
    def singularity_cache_internal_dir(self) -> Path:
        """Get Singularity internal cache directory."""
        cache_dir = Path(self.get("singularity.cache_internal_dir"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @property
    def results_dir(self) -> Path:
        """Get results directory."""
        results_dir = Path(self.get("integration.results_dir"))
        results_dir.mkdir(parents=True, exist_ok=True)
        return results_dir

    @property
    def repo_mapping(self) -> Dict[str, str]:
        """Get repository name mapping."""
        return self.get("repo_mapping", {})

    def get_repo_name(self, full_repo: str) -> str:
        """
        Get short repository name from full name.

        Args:
            full_repo: Full repository name (e.g., "pytest-dev/pytest")

        Returns:
            Short name (e.g., "pytest")
        """
        return self.repo_mapping.get(full_repo, full_repo.split("/")[-1])

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self._config.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"Config({len(self._config)} sections loaded)"


# Global configuration instance
_global_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance.

    Args:
        config_path: Optional path to config file (only used on first call)

    Returns:
        Configuration instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config(config_path)
    return _global_config


def reset_config():
    """Reset global configuration instance."""
    global _global_config
    _global_config = None
