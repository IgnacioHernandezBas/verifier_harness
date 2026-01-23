#!/usr/bin/env python3
"""
Claim Validation Script for astropy__astropy-7746
==================================================

This script:
1. Applies grounding check to extracted claims
2. Synchronizes confidence_factors.diff_grounded with grounding.is_grounded
3. Re-calculates claim confidence based on the confidence matrix
4. Saves updated claims with correct metadata
"""

import json
from grounding import (
    extract_symbols_from_diff,
    filter_grounded_claims,
    print_grounding_analysis
)


def calculate_confidence(claim):
    """
    Calculate claim confidence based on the confidence matrix from documentation.

    Matrix (Section 3.4):
    | Specificity | Grounding | Observability | → Confidence |
    |-------------|-----------|---------------|--------------|
    | Explicit    | Strong    | High          | HIGH         |
    | Explicit    | Weak      | High          | HIGH         |
    | Implied     | Strong    | High          | MEDIUM       |
    | Implied     | Weak      | Medium        | MEDIUM       |
    | Vague       | Any       | Any           | LOW          |
    | Any         | None      | Any           | LOW          |
    """
    if 'confidence_factors' not in claim:
        return claim.get('confidence', 'medium')

    factors = claim['confidence_factors']
    specificity = factors.get('requirement_specificity', 'explicit')
    grounded = factors.get('diff_grounded', False)
    observability = factors.get('observability', 'high')

    # Get grounding strength from grounding metadata
    grounding_strength = 'none'
    if 'grounding' in claim:
        grounding_strength = claim['grounding'].get('strength', 'none')

    # Rule 1: Vague requirements → LOW
    if specificity == 'vague':
        return 'low'

    # Rule 2: Not grounded → LOW
    if not grounded or grounding_strength == 'none':
        return 'low'

    # Rule 3: Explicit + (Strong or Weak) + High → HIGH
    if specificity == 'explicit' and observability == 'high':
        return 'high'

    # Rule 4: Implied + Strong + High → MEDIUM
    if specificity == 'implied' and grounding_strength == 'strong' and observability == 'high':
        return 'medium'

    # Rule 5: Implied + Weak + Medium → MEDIUM
    if specificity == 'implied' and observability == 'medium':
        return 'medium'

    # Default
    return 'medium'


def sync_confidence_factors(claims):
    """
    Synchronize confidence_factors.diff_grounded with grounding.is_grounded
    and recalculate confidence.
    """
    updated_count = 0
    confidence_changed = 0

    for claim in claims:
        if 'grounding' not in claim or 'confidence_factors' not in claim:
            continue

        # Get grounding result
        is_grounded = claim['grounding'].get('is_grounded', False)
        old_diff_grounded = claim['confidence_factors'].get('diff_grounded', False)
        old_confidence = claim.get('confidence', 'medium')

        # Update diff_grounded
        claim['confidence_factors']['diff_grounded'] = is_grounded

        # Recalculate confidence
        new_confidence = calculate_confidence(claim)
        claim['confidence'] = new_confidence

        # Track changes
        if old_diff_grounded != is_grounded:
            updated_count += 1

        if old_confidence != new_confidence:
            confidence_changed += 1
            print(f"  {claim['claim_id']}: confidence {old_confidence} → {new_confidence}")

    return updated_count, confidence_changed


# Load issue
with open('./validation_issues.json', 'r') as f:
    issues = json.load(f)

issue = issues['astropy__astropy-7746']
patch = issue['patch']

print("="*70)
print("ASTROPY__ASTROPY-7746 - CLAIM VALIDATION")
print("="*70)

# Extract symbols from patch
symbols = extract_symbols_from_diff(patch)
print(f"\nSymbols in patch: {symbols}")

# Load claims
with open('./claims/astropy__astropy-7746.json', 'r') as f:
    claim_data = json.load(f)

claims = claim_data['claims']
print(f"\nTotal claims extracted: {len(claims)}")

# Show original state
print(f"\n{'='*70}")
print("ORIGINAL CONFIDENCE STATE:")
print(f"{'='*70}")
for claim in claims:
    cf = claim.get('confidence_factors', {})
    print(f"  {claim['claim_id']}: confidence={claim.get('confidence')}, "
          f"diff_grounded={cf.get('diff_grounded', 'N/A')}")

# Apply grounding check
print(f"\n{'='*70}")
print("APPLYING GROUNDING CHECK...")
print(f"{'='*70}")
grounded, ungrounded = filter_grounded_claims(claims, patch, min_strength='weak')

print(f"\n✅ GROUNDED: {len(grounded)}/{len(claims)} ({len(grounded)/len(claims)*100:.0f}%)")
for claim in grounded:
    print(f"\n  {claim['claim_id']}: {claim['claim_text'][:60]}...")
    print(f"    Targets: {claim['target_symbols']}")
    print(f"    Grounding: {claim['grounding']['strength']} "
          f"(matched: {claim['grounding']['matched_symbols']})")
    print(f"    Match ratio: {claim['grounding']['match_ratio']:.1%}")

if ungrounded:
    print(f"\n❌ NOT GROUNDED: {len(ungrounded)}/{len(claims)} ({len(ungrounded)/len(claims)*100:.0f}%)")
    for claim in ungrounded:
        print(f"\n  {claim['claim_id']}: {claim['claim_text'][:60]}...")
        print(f"    Targets: {claim['target_symbols']}")

# Sync confidence factors and recalculate confidence
print(f"\n{'='*70}")
print("SYNCHRONIZING CONFIDENCE FACTORS...")
print(f"{'='*70}")

all_claims = grounded + ungrounded
updated, conf_changed = sync_confidence_factors(all_claims)

print(f"\n  diff_grounded fields updated: {updated}")
print(f"  Confidence values changed: {conf_changed}")

# Show updated state
print(f"\n{'='*70}")
print("UPDATED CONFIDENCE STATE:")
print(f"{'='*70}")
for claim in all_claims:
    cf = claim.get('confidence_factors', {})
    grounding = claim.get('grounding', {})
    print(f"  {claim['claim_id']}: confidence={claim.get('confidence')}, "
          f"diff_grounded={cf.get('diff_grounded', 'N/A')}, "
          f"is_grounded={grounding.get('is_grounded', 'N/A')}, "
          f"strength={grounding.get('strength', 'N/A')}")

# Save updated claims
claim_data['claims'] = all_claims
with open('./claims/astropy__astropy-7746.json', 'w') as f:
    json.dump(claim_data, f, indent=2)

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"  Total claims: {len(all_claims)}")
print(f"  Grounded: {len(grounded)} ({len(grounded)/len(all_claims)*100:.0f}%)")
print(f"  High confidence: {sum(1 for c in all_claims if c.get('confidence') == 'high')}")
print(f"  Medium confidence: {sum(1 for c in all_claims if c.get('confidence') == 'medium')}")
print(f"  Low confidence: {sum(1 for c in all_claims if c.get('confidence') == 'low')}")

print(f"\n✅ Claims file updated: ./claims/astropy__astropy-7746.json")
print(f"\nNext step: Generate tests for HIGH confidence, grounded claims")
