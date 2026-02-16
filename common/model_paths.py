"""
Utilities for organizing outputs by model.

This module provides consistent path management for multi-model workflows,
enabling users to:
- Extract claims with Model A and generate tests with Model B
- Compare outputs across different models
- Track which model was used at each stage

Directory structure:
    claim_extraction/claims_out/{model_slug}/{instance_id}.json
    claim_test_generation/tests_out/{model_slug}/{instance_id}/test_*.py
    agentic_closed_loop/state/{model_slug}/{instance_id}_{claim_id}.json
    agentic_closed_loop/logs/{model_slug}/{instance_id}_{claim_id}.jsonl
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def slugify_model_name(model_name: str) -> str:
    """
    Convert a model name to a filesystem-safe slug.

    Examples:
        Qwen/Qwen2.5-Coder-32B-Instruct-AWQ -> Qwen2.5-Coder-32B-Instruct-AWQ
        meta-llama/Llama-3.1-70B-Instruct -> Llama-3.1-70B-Instruct
        gpt-4-turbo-2024-04-09 -> gpt-4-turbo-2024-04-09
        claude-3-5-sonnet-20241022 -> claude-3-5-sonnet-20241022
    """
    # Remove organization prefix (e.g., "Qwen/", "meta-llama/")
    slug = model_name.split('/')[-1]

    # Replace any remaining unsafe characters with hyphens
    slug = re.sub(r'[^\w\-.]', '-', slug)

    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens
    slug = slug.strip('-')

    return slug


class ModelPaths:
    """
    Manages model-specific directory paths.

    Usage:
        paths = ModelPaths(
            model_name="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
            base_dir="/path/to/verifier_harness"
        )

        # Get claims directory for this model
        claims_dir = paths.claims_dir()

        # Get path for a specific claim file
        claim_file = paths.claim_file("django__django-13321")

        # Get tests directory for this model
        tests_dir = paths.tests_dir("django__django-13321")

        # Get state file path
        state_file = paths.state_file("django__django-13321", "C1")
    """

    def __init__(
        self,
        model_name: str,
        base_dir: Optional[Path] = None,
        use_model_subdirs: bool = True,
    ):
        """
        Initialize model paths.

        Args:
            model_name: Full model name (e.g., "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ")
            base_dir: Base directory (defaults to current working directory)
            use_model_subdirs: If False, use legacy flat structure (for backwards compatibility)
        """
        self.model_name = model_name
        self.model_slug = slugify_model_name(model_name)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.use_model_subdirs = use_model_subdirs

    def claims_dir(self) -> Path:
        """Get the claims output directory for this model."""
        if self.use_model_subdirs:
            return self.base_dir / "claim_extraction" / "claims_out" / self.model_slug
        else:
            # Legacy: flat structure
            return self.base_dir / "claim_extraction" / "claims_out"

    def claim_file(self, instance_id: str) -> Path:
        """Get the path to a specific claim file."""
        return self.claims_dir() / f"{instance_id}.json"

    def claims_summary(self) -> Path:
        """Get the path to the claims summary file."""
        return self.claims_dir() / "summary.json"

    def tests_dir(self, instance_id: str) -> Path:
        """Get the tests directory for a specific instance."""
        if self.use_model_subdirs:
            return self.base_dir / "claim_test_generation" / "tests_out" / self.model_slug / instance_id
        else:
            # Legacy: flat structure
            return self.base_dir / "claim_test_generation" / "tests_out" / instance_id

    def tests_root(self) -> Path:
        """Get the tests root directory for this model."""
        if self.use_model_subdirs:
            return self.base_dir / "claim_test_generation" / "tests_out" / self.model_slug
        else:
            return self.base_dir / "claim_test_generation" / "tests_out"

    def state_dir(self) -> Path:
        """Get the state directory for this model."""
        if self.use_model_subdirs:
            return self.base_dir / "agentic_closed_loop" / "state" / self.model_slug
        else:
            # Legacy: flat structure
            return self.base_dir / "agentic_closed_loop" / "state"

    def state_file(self, instance_id: str, claim_id: str = "C1") -> Path:
        """Get the state file path for a specific instance and claim."""
        return self.state_dir() / f"{instance_id}_{claim_id}.json"

    def logs_dir(self) -> Path:
        """Get the logs directory for this model."""
        if self.use_model_subdirs:
            return self.base_dir / "agentic_closed_loop" / "logs" / self.model_slug
        else:
            # Legacy: flat structure (no dedicated logs dir in legacy)
            return self.base_dir / "agentic_closed_loop" / "logs"

    def log_file(self, instance_id: str, claim_id: str = "C1") -> Path:
        """Get the log file path for a specific instance and claim."""
        return self.logs_dir() / f"{instance_id}_{claim_id}.jsonl"

    def ensure_dirs(self) -> None:
        """Create all necessary directories for this model."""
        self.claims_dir().mkdir(parents=True, exist_ok=True)
        self.tests_root().mkdir(parents=True, exist_ok=True)
        self.state_dir().mkdir(parents=True, exist_ok=True)
        self.logs_dir().mkdir(parents=True, exist_ok=True)


class MultiModelPaths:
    """
    Manages paths for multi-model workflows (e.g., claims from Model A, tests from Model B).

    Usage:
        paths = MultiModelPaths(
            claims_model="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
            tests_model="deepseek-ai/DeepSeek-V3",
            base_dir="/path/to/verifier_harness"
        )

        # Get claims from Model A
        claim_file = paths.claim_file("django__django-13321")

        # Write tests with Model B
        test_dir = paths.tests_dir("django__django-13321")
    """

    def __init__(
        self,
        claims_model: str,
        tests_model: Optional[str] = None,
        base_dir: Optional[Path] = None,
        use_model_subdirs: bool = True,
    ):
        """
        Initialize multi-model paths.

        Args:
            claims_model: Model used for claim extraction
            tests_model: Model used for test generation (defaults to claims_model)
            base_dir: Base directory
            use_model_subdirs: Whether to use model-specific subdirectories
        """
        self.claims_model = claims_model
        self.tests_model = tests_model or claims_model
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.use_model_subdirs = use_model_subdirs

        # Create separate path managers for claims and tests
        self.claims_paths = ModelPaths(
            model_name=claims_model,
            base_dir=base_dir,
            use_model_subdirs=use_model_subdirs,
        )
        self.tests_paths = ModelPaths(
            model_name=self.tests_model,
            base_dir=base_dir,
            use_model_subdirs=use_model_subdirs,
        )

    # Delegate claims-related methods to claims_paths
    def claims_dir(self) -> Path:
        return self.claims_paths.claims_dir()

    def claim_file(self, instance_id: str) -> Path:
        return self.claims_paths.claim_file(instance_id)

    def claims_summary(self) -> Path:
        return self.claims_paths.claims_summary()

    # Delegate tests-related methods to tests_paths
    def tests_dir(self, instance_id: str) -> Path:
        return self.tests_paths.tests_dir(instance_id)

    def tests_root(self) -> Path:
        return self.tests_paths.tests_root()

    def state_dir(self) -> Path:
        return self.tests_paths.state_dir()

    def state_file(self, instance_id: str, claim_id: str = "C1") -> Path:
        return self.tests_paths.state_file(instance_id, claim_id)

    def logs_dir(self) -> Path:
        return self.tests_paths.logs_dir()

    def log_file(self, instance_id: str, claim_id: str = "C1") -> Path:
        return self.tests_paths.log_file(instance_id, claim_id)

    def ensure_dirs(self) -> None:
        """Create all necessary directories for both models."""
        self.claims_paths.ensure_dirs()
        self.tests_paths.ensure_dirs()

    def get_summary(self) -> dict:
        """Get a summary of the multi-model configuration."""
        return {
            "claims_model": self.claims_model,
            "claims_model_slug": self.claims_paths.model_slug,
            "tests_model": self.tests_model,
            "tests_model_slug": self.tests_paths.model_slug,
            "use_model_subdirs": self.use_model_subdirs,
            "claims_dir": str(self.claims_dir()),
            "tests_root": str(self.tests_root()),
            "state_dir": str(self.state_dir()),
            "logs_dir": str(self.logs_dir()),
        }
