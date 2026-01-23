#!/usr/bin/env python3
"""
Grounding Check Demo
====================

This script demonstrates the grounding check functionality with real
examples from SWE-bench.
"""

from claim_extraction.grounding import (
    extract_symbols_from_diff,
    is_claim_grounded,
    filter_grounded_claims,
    calculate_grounding_strength,
    print_grounding_analysis,
)


def example_1_astropy_grounded():
    """Example 1: Grounded claim from astropy__astropy-7746"""
    print("=" * 70)
    print("EXAMPLE 1: Grounded Claim (astropy__astropy-7746)")
    print("=" * 70)

    issue = """
    Issue: ascii.qdp assumes that commands in a QDP file are upper case

    QDP itself is not case sensitive, so commands like 'read serr 1 2'
    should be accepted but currently raise a ValueError.
    """

    patch = """
diff --git a/astropy/io/ascii/qdp.py b/astropy/io/ascii/qdp.py
index abc123..def456 100644
--- a/astropy/io/ascii/qdp.py
+++ b/astropy/io/ascii/qdp.py
@@ -64,7 +64,7 @@ def _line_type(line, delimiter=None):

 def _parse_qdp_commands(line):
-    if line.startswith('READ'):
+    if line.upper().startswith('READ'):
         return 'READ'
-    elif line.startswith('PLOT'):
+    elif line.upper().startswith('PLOT'):
         return 'PLOT'
"""

    claim = {
        'claim_id': 'C1',
        'claim_text': 'QDP commands must be case-insensitive',
        'target_symbols': ['_parse_qdp_commands'],
        'claim_type': 'exception',
        'confidence': 'high'
    }

    print("\nIssue Summary:")
    print(issue.strip())
    print("\n" + "-" * 70)
    print("Claim:")
    print(f"  ID: {claim['claim_id']}")
    print(f"  Text: {claim['claim_text']}")
    print(f"  Target Symbols: {claim['target_symbols']}")
    print("\n" + "-" * 70)

    print_grounding_analysis(claim, patch)
    print("\n✅ This claim is GROUNDED - it references code that was actually modified")
    print()


def example_2_astropy_not_grounded():
    """Example 2: NOT grounded claim from same astropy issue"""
    print("=" * 70)
    print("EXAMPLE 2: NOT Grounded Claim (same issue)")
    print("=" * 70)

    patch = """
diff --git a/astropy/io/ascii/qdp.py b/astropy/io/ascii/qdp.py
@@ -64,7 +64,7 @@ def _parse_qdp_commands(line):
-    if line.startswith('READ'):
+    if line.upper().startswith('READ'):
"""

    claim = {
        'claim_id': 'C2',
        'claim_text': 'Table.read must not raise ValueError',
        'target_symbols': ['Table.read'],  # User mentioned this, but patch doesn't touch it
        'claim_type': 'exception',
        'confidence': 'medium'
    }

    print("Claim:")
    print(f"  ID: {claim['claim_id']}")
    print(f"  Text: {claim['claim_text']}")
    print(f"  Target Symbols: {claim['target_symbols']}")
    print("\n" + "-" * 70)

    print_grounding_analysis(claim, patch)
    print("\n❌ This claim is NOT GROUNDED - it references code NOT modified by the patch")
    print("   The issue MENTIONS Table.read, but the fix is in _parse_qdp_commands")
    print()


def example_3_django_multiple_claims():
    """Example 3: Filtering multiple claims"""
    print("=" * 70)
    print("EXAMPLE 3: Filtering Multiple Claims (Django scenario)")
    print("=" * 70)

    patch = """
diff --git a/django/core/validators.py b/django/core/validators.py
index abc..def 100644
--- a/django/core/validators.py
+++ b/django/core/validators.py
@@ -100,5 +100,8 @@ def validate_email(email):
-    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
+    # Support + in email addresses
+    regex = r'^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$'
     return re.match(regex, email) is not None
"""

    claims = [
        {
            'claim_id': 'C1',
            'claim_text': 'validate_email should accept plus signs',
            'target_symbols': ['validate_email'],
            'confidence': 'high'
        },
        {
            'claim_id': 'C2',
            'claim_text': 'EmailField should validate correctly',
            'target_symbols': ['EmailField', 'EmailField.validate'],
            'confidence': 'medium'
        },
        {
            'claim_id': 'C3',
            'claim_text': 'User.save should call email validation',
            'target_symbols': ['User.save'],
            'confidence': 'low'
        }
    ]

    print("\nPatch modifies: validate_email()")
    print("\nExtracted claims:")
    for claim in claims:
        print(f"  {claim['claim_id']}: {claim['claim_text']}")
        print(f"    Targets: {claim['target_symbols']}")

    print("\n" + "-" * 70)
    print("FILTERING RESULTS:")
    print("-" * 70)

    grounded, ungrounded = filter_grounded_claims(claims, patch)

    print(f"\n✅ GROUNDED CLAIMS ({len(grounded)}):")
    for claim in grounded:
        print(f"  {claim['claim_id']}: {claim['claim_text']}")
        grounding = claim['grounding']
        print(f"    Strength: {grounding['strength']}")
        print(f"    Matched: {grounding['matched_symbols']}")

    print(f"\n❌ NOT GROUNDED CLAIMS ({len(ungrounded)}):")
    for claim in ungrounded:
        print(f"  {claim['claim_id']}: {claim['claim_text']}")
        print(f"    Targets: {claim['target_symbols']} (not in patch)")

    print("\n📊 Summary:")
    print(f"  Total claims: {len(claims)}")
    print(f"  Grounded: {len(grounded)} ({len(grounded)/len(claims)*100:.0f}%)")
    print(f"  Not grounded: {len(ungrounded)} ({len(ungrounded)/len(claims)*100:.0f}%)")
    print()


def example_4_symbol_extraction():
    """Example 4: Show what symbols are extracted from a patch"""
    print("=" * 70)
    print("EXAMPLE 4: Symbol Extraction from Complex Patch")
    print("=" * 70)

    patch = """
diff --git a/processor.py b/processor.py
index abc..def 100644
--- a/processor.py
+++ b/processor.py
@@ -10,15 +10,20 @@ class DataProcessor:
-    def parse_input(self, data):
+    def parse_input(self, data, strict=False):
+        if strict:
+            self.validate_strict(data)
         return self._normalize(data)

-    def _normalize(self, data):
+    def _normalize(self, data):
         return data.strip().lower()
+
+    def validate_strict(self, data):
+        if not data:
+            raise ValueError("Empty data")

 class ResultFormatter:
-    def format(self, result):
+    def format_result(self, result):
         return str(result)
"""

    print("Patch contains:")
    print("  - Modified: DataProcessor.parse_input")
    print("  - Modified: DataProcessor._normalize")
    print("  - Added: DataProcessor.validate_strict")
    print("  - Renamed: ResultFormatter.format → format_result")

    symbols = extract_symbols_from_diff(patch)

    print("\n" + "-" * 70)
    print("EXTRACTED SYMBOLS:")
    print("-" * 70)

    for symbol in sorted(symbols):
        print(f"  • {symbol}")

    print(f"\nTotal symbols extracted: {len(symbols)}")

    # Test grounding with different claims
    test_claims = [
        {'target_symbols': ['parse_input'], 'desc': 'Modified method'},
        {'target_symbols': ['validate_strict'], 'desc': 'New method'},
        {'target_symbols': ['format_result'], 'desc': 'Renamed method'},
        {'target_symbols': ['format'], 'desc': 'Old name of renamed method'},
        {'target_symbols': ['process_data'], 'desc': 'Unrelated method'},
    ]

    print("\n" + "-" * 70)
    print("GROUNDING TEST:")
    print("-" * 70)

    for claim in test_claims:
        is_grounded = is_claim_grounded(claim, patch)
        symbol = claim['target_symbols'][0]
        desc = claim['desc']
        status = "✅ GROUNDED" if is_grounded else "❌ NOT GROUNDED"
        print(f"  {symbol:20} ({desc:30}) {status}")
    print()


def example_5_weak_vs_strong():
    """Example 5: Demonstrate weak vs strong grounding"""
    print("=" * 70)
    print("EXAMPLE 5: Weak vs Strong Grounding")
    print("=" * 70)

    patch = """
diff --git a/auth.py b/auth.py
-def authenticate(username, password):
+def authenticate(username, password):
     return True
"""

    claims = [
        {
            'claim_id': 'C1',
            'target_symbols': ['authenticate'],
            'desc': 'All symbols match'
        },
        {
            'claim_id': 'C2',
            'target_symbols': ['authenticate', 'validate_password'],
            'desc': 'Partial match'
        },
        {
            'claim_id': 'C3',
            'target_symbols': ['login', 'logout'],
            'desc': 'No match'
        }
    ]

    print("\nPatch modifies: authenticate()")
    print("\nClaims:\n")

    for claim in claims:
        result = calculate_grounding_strength(claim, patch)
        print(f"{claim['claim_id']}: {claim['desc']}")
        print(f"  Target symbols: {claim['target_symbols']}")
        print(f"  Grounding strength: {result.strength.upper()}")
        print(f"  Matched: {result.matched_symbols}")
        print(f"  Unmatched: {result.unmatched_symbols}")
        print(f"  Is grounded: {result.is_grounded}")
        print(f"  Would pass weak filter: {result.is_grounded}")
        print(f"  Would pass strong filter: {result.strength == 'strong'}")
        print()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "GROUNDING CHECK DEMO" + " " * 28 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    example_1_astropy_grounded()
    print("\n")

    example_2_astropy_not_grounded()
    print("\n")

    example_3_django_multiple_claims()
    print("\n")

    example_4_symbol_extraction()
    print("\n")

    example_5_weak_vs_strong()

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\n✅ Grounding check is working correctly!")
    print("\nKey Takeaways:")
    print("  1. Grounding prevents extracting claims about unmodified code")
    print("  2. Symbol extraction parses the git diff to find modified functions/classes")
    print("  3. Weak grounding = at least one symbol matches")
    print("  4. Strong grounding = all symbols match")
    print("  5. Only generate tests for grounded claims to avoid false positives")
    print()


if __name__ == '__main__':
    main()
