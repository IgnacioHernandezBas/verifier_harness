"""
Verifier Package - Unified verification system for SWE-bench patches.

This package provides static and dynamic analysis tools for evaluating
AI-generated code patches.

The multi-layer harness interconnects:
  - Layer 1: Static analysis (pylint, flake8, radon, mypy, bandit, AST)
  - Layer 2: Unit-test execution (Singularity / Podman containers)
  - Layer 3: Claim-test generation & BUG/GOLD verification
"""

__version__ = "0.2.0"

from verifier.multi_layer_harness import (
    HarnessReport,
    LayerResult,
    MultiLayerHarness,
    Verdict,
)

__all__ = [
    "MultiLayerHarness",
    "HarnessReport",
    "LayerResult",
    "Verdict",
]
