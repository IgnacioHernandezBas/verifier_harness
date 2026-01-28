"""
Claim Schema Module
===================

Defines the data structures for behavioral claims extracted from GitHub issues.
Based on the JSON Schema defined in the project documentation (Apéndice A).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Literal, Optional, Dict
from datetime import datetime
from enum import Enum


class ClaimType(str, Enum):
    """Types of behavioral claims."""
    RETURN = "return"
    EXCEPTION = "exception"
    INVARIANT = "invariant"
    STATE_CHANGE = "state_change"


class Confidence(str, Enum):
    """Confidence levels for claims."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Specificity(str, Enum):
    """Requirement specificity levels."""
    EXPLICIT = "explicit"
    IMPLIED = "implied"
    VAGUE = "vague"


class Observability(str, Enum):
    """Observability/testability levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ConfidenceFactors:
    """Factors that determine claim confidence."""
    requirement_specificity: Specificity
    diff_grounded: bool
    observability: Observability

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'requirement_specificity': self.requirement_specificity.value,
            'diff_grounded': self.diff_grounded,
            'observability': self.observability.value
        }


@dataclass
class Evidence:
    """Evidence supporting a claim from the issue text."""
    spans: List[str] = field(default_factory=list)
    line_numbers: Optional[List[int]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = {'spans': self.spans}
        if self.line_numbers is not None:
            result['line_numbers'] = self.line_numbers
        return result


@dataclass
class Claim:
    """
    A behavioral claim extracted from a GitHub issue.

    Represents a testable assertion about the expected behavior of code,
    structured in Given-When-Then format.
    """

    # Required fields
    claim_id: str  # Pattern: C1, C2, C3, etc.
    claim_type: ClaimType
    claim_text: str
    confidence: Confidence
    target_symbols: List[str]  # Functions/classes this claim references

    # Given-When-Then structure
    given: str  # Context/preconditions
    when: str   # Action/trigger
    then: str   # Expected outcome

    # Optional fields
    confidence_factors: Optional[ConfidenceFactors] = None
    evidence: Optional[Evidence] = None

    # Grounding metadata (added by grounding check)
    grounding: Optional[Dict] = None

    def __post_init__(self):
        """Validate claim after initialization."""
        # Validate claim_id format
        if not self.claim_id.startswith('C') or not self.claim_id[1:].isdigit():
            raise ValueError(f"claim_id must match pattern 'C[0-9]+', got: {self.claim_id}")

        # Validate claim_text minimum length
        if len(self.claim_text) < 10:
            raise ValueError(f"claim_text must be at least 10 characters, got: {len(self.claim_text)}")

        # Validate target_symbols not empty
        if not self.target_symbols:
            raise ValueError("target_symbols must contain at least one symbol")

        # Convert enums if needed
        if isinstance(self.claim_type, str):
            self.claim_type = ClaimType(self.claim_type)
        if isinstance(self.confidence, str):
            self.confidence = Confidence(self.confidence)

    def to_dict(self) -> Dict:
        """Convert claim to dictionary for JSON serialization."""
        result = {
            'claim_id': self.claim_id,
            'claim_type': self.claim_type.value,
            'claim_text': self.claim_text,
            'given': self.given,
            'when': self.when,
            'then': self.then,
            'confidence': self.confidence.value,
            'target_symbols': self.target_symbols
        }

        if self.confidence_factors:
            result['confidence_factors'] = self.confidence_factors.to_dict()

        if self.evidence:
            result['evidence'] = self.evidence.to_dict()

        if self.grounding:
            result['grounding'] = self.grounding

        return result


@dataclass
class ClaimSet:
    """
    A set of claims extracted from a single SWE-bench instance.
    """
    instance_id: str
    claims: List[Claim]
    extraction_model: Optional[str] = None  # e.g., "manual", "claude-sonnet-4.5", "qwen2.5-32b"
    extraction_timestamp: Optional[str] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.extraction_timestamp is None:
            self.extraction_timestamp = datetime.utcnow().isoformat() + 'Z'

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'instance_id': self.instance_id,
            'extraction_model': self.extraction_model,
            'extraction_timestamp': self.extraction_timestamp,
            'claims': [claim.to_dict() for claim in self.claims]
        }

    def add_claim(self, claim: Claim) -> None:
        """Add a claim to the set."""
        self.claims.append(claim)

    def get_grounded_claims(self) -> List[Claim]:
        """Get only grounded claims."""
        return [c for c in self.claims if c.grounding and c.grounding.get('is_grounded')]

    def get_high_confidence_claims(self) -> List[Claim]:
        """Get only high-confidence claims."""
        return [c for c in self.claims if c.confidence == Confidence.HIGH]

    def grounding_rate(self) -> float:
        """Calculate grounding rate."""
        if not self.claims:
            return 0.0
        grounded = len(self.get_grounded_claims())
        return grounded / len(self.claims)


# Helper functions for creating claims

def create_claim(
    claim_id: str,
    claim_text: str,
    claim_type: ClaimType | str,
    given: str,
    when: str,
    then: str,
    target_symbols: List[str],
    confidence: Confidence | str = Confidence.HIGH,
    requirement_specificity: Specificity | str = Specificity.EXPLICIT,
    observability: Observability | str = Observability.HIGH,
    evidence_spans: Optional[List[str]] = None
) -> Claim:
    """
    Helper function to create a Claim with all required fields.

    Args:
        claim_id: Unique ID (C1, C2, etc.)
        claim_text: Human-readable description
        claim_type: Type of claim (return, exception, invariant, state_change)
        given: Context/preconditions
        when: Action/trigger
        then: Expected outcome
        target_symbols: Functions/classes referenced
        confidence: Confidence level
        requirement_specificity: How explicit the requirement is
        observability: How testable the behavior is
        evidence_spans: Text spans from issue supporting the claim

    Returns:
        Claim object
    """
    # Convert strings to enums if needed
    if isinstance(claim_type, str):
        claim_type = ClaimType(claim_type)
    if isinstance(confidence, str):
        confidence = Confidence(confidence)
    if isinstance(requirement_specificity, str):
        requirement_specificity = Specificity(requirement_specificity)
    if isinstance(observability, str):
        observability = Observability(observability)

    confidence_factors = ConfidenceFactors(
        requirement_specificity=requirement_specificity,
        diff_grounded=False,  # Will be set by grounding check
        observability=observability
    )

    evidence = None
    if evidence_spans:
        evidence = Evidence(spans=evidence_spans)

    return Claim(
        claim_id=claim_id,
        claim_type=claim_type,
        claim_text=claim_text,
        given=given,
        when=when,
        then=then,
        confidence=confidence,
        target_symbols=target_symbols,
        confidence_factors=confidence_factors,
        evidence=evidence
    )
