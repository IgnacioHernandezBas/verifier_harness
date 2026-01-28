"""
Claim Extraction Module
=======================

This module handles the extraction and validation of behavioral claims
from GitHub issues and their corresponding patches.

Components:
- grounding: Symbol extraction and claim-to-patch grounding verification
- schema: JSON schema and dataclasses for claims (future)
- extraction: LLM-based claim extraction (future)
- test_generation: Claim-to-pytest test generation (future)
"""

__version__ = "0.1.0"

from .grounding import (
    extract_symbols_from_diff,
    is_claim_grounded,
    filter_grounded_claims,
    calculate_grounding_strength,
    GroundingResult,
)

__all__ = [
    "extract_symbols_from_diff",
    "is_claim_grounded",
    "filter_grounded_claims",
    "calculate_grounding_strength",
    "GroundingResult",
]
