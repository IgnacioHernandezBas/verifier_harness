"""
Tests for Grounding Module
===========================

Tests the claim grounding functionality with realistic examples
from SWE-bench patches.
"""

import pytest
from claim_extraction.grounding import (
    extract_symbols_from_diff,
    is_claim_grounded,
    filter_grounded_claims,
    calculate_grounding_strength,
    normalize_symbol,
)


class TestExtractSymbolsFromDiff:
    """Test symbol extraction from git diffs."""

    def test_extract_function_definition(self):
        """Should extract function names from def statements."""
        patch = """
diff --git a/module.py b/module.py
@@ -10,5 +10,5 @@
-def old_function():
+def new_function():
     pass
"""
        symbols = extract_symbols_from_diff(patch)
        assert 'old_function' in symbols
        assert 'new_function' in symbols

    def test_extract_class_definition(self):
        """Should extract class names from class statements."""
        patch = """
diff --git a/models.py b/models.py
@@ -20,3 +20,3 @@
-class OldModel:
+class NewModel(BaseModel):
     pass
"""
        symbols = extract_symbols_from_diff(patch)
        assert 'OldModel' in symbols
        assert 'NewModel' in symbols

    def test_astropy_qdp_example(self):
        """Real example from astropy__astropy-7746."""
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
        symbols = extract_symbols_from_diff(patch)
        # Should extract the function that was modified
        assert '_parse_qdp_commands' in symbols
        # Should also extract methods called in the changes
        assert 'upper' in symbols or 'startswith' in symbols

    def test_empty_patch(self):
        """Should return empty set for empty patch."""
        symbols = extract_symbols_from_diff("")
        assert symbols == set()

    def test_method_modification(self):
        """Should extract class methods."""
        patch = """
diff --git a/class_file.py b/class_file.py
@@ -30,5 +30,5 @@
 class MyClass:
-    def old_method(self):
+    def new_method(self):
         pass
"""
        symbols = extract_symbols_from_diff(patch)
        assert 'old_method' in symbols
        assert 'new_method' in symbols
        assert 'MyClass' in symbols

    def test_multiple_files(self):
        """Should extract symbols from multiple files in patch."""
        patch = """
diff --git a/file1.py b/file1.py
-def func_a():
+def func_a_new():
     pass

diff --git a/file2.py b/file2.py
-def func_b():
+def func_b_new():
     pass
"""
        symbols = extract_symbols_from_diff(patch)
        assert 'func_a' in symbols
        assert 'func_a_new' in symbols
        assert 'func_b' in symbols
        assert 'func_b_new' in symbols


class TestNormalizeSymbol:
    """Test symbol normalization."""

    def test_simple_symbol(self):
        """Simple symbol should return itself."""
        variants = normalize_symbol('function_name')
        assert 'function_name' in variants

    def test_dotted_symbol(self):
        """Dotted symbol should split into parts."""
        variants = normalize_symbol('Table.read')
        assert 'Table' in variants
        assert 'read' in variants
        assert 'Table.read' in variants

    def test_method_symbol(self):
        """Method notation should split."""
        variants = normalize_symbol('MyClass.my_method')
        assert 'MyClass' in variants
        assert 'my_method' in variants
        assert 'MyClass.my_method' in variants


class TestIsClaimGrounded:
    """Test claim grounding check."""

    def test_grounded_claim_simple(self):
        """Claim with matching symbol should be grounded."""
        claim = {'target_symbols': ['parse_command']}
        patch = """
-def parse_command(line):
+def parse_command(line):
     return line.upper()
"""
        assert is_claim_grounded(claim, patch) is True

    def test_ungrounded_claim(self):
        """Claim with no matching symbols should not be grounded."""
        claim = {'target_symbols': ['validate_input']}
        patch = """
-def parse_command(line):
+def parse_command(line):
     return line.upper()
"""
        assert is_claim_grounded(claim, patch) is False

    def test_partial_grounding_weak(self):
        """Claim with some matching symbols should be weakly grounded."""
        claim = {'target_symbols': ['parse_command', 'validate_input']}
        patch = """
-def parse_command(line):
+def parse_command(line):
     return line.upper()
"""
        # Should pass with default weak grounding
        assert is_claim_grounded(claim, patch, require_strong=False) is True
        # Should fail with strong grounding requirement
        assert is_claim_grounded(claim, patch, require_strong=True) is False

    def test_dotted_symbol_grounding(self):
        """Should handle dotted symbols like Table.read."""
        claim = {'target_symbols': ['Table.read']}
        patch = """
diff --git a/table.py b/table.py
@@ -10,5 +10,5 @@
 class Table:
-    def read(self, file):
+    def read(self, file, format=None):
         pass
"""
        # Should match because 'read' method is modified
        assert is_claim_grounded(claim, patch) is True

    def test_astropy_example_grounded(self):
        """Real grounded example from astropy."""
        claim = {
            'claim_id': 'C1',
            'target_symbols': ['_parse_qdp_commands'],
            'claim_text': 'QDP commands should be case-insensitive'
        }
        patch = """
diff --git a/astropy/io/ascii/qdp.py b/astropy/io/ascii/qdp.py
-def _parse_qdp_commands(line):
-    if line.startswith('READ'):
+def _parse_qdp_commands(line):
+    if line.upper().startswith('READ'):
"""
        assert is_claim_grounded(claim, patch) is True

    def test_astropy_example_not_grounded(self):
        """Real ungrounded example from astropy."""
        claim = {
            'claim_id': 'C2',
            'target_symbols': ['Table.read'],  # Issue mentions this but patch doesn't touch it
            'claim_text': 'Table.read should handle QDP files'
        }
        patch = """
diff --git a/astropy/io/ascii/qdp.py b/astropy/io/ascii/qdp.py
-def _parse_qdp_commands(line):
-    if line.startswith('READ'):
+def _parse_qdp_commands(line):
+    if line.upper().startswith('READ'):
"""
        assert is_claim_grounded(claim, patch) is False


class TestCalculateGroundingStrength:
    """Test detailed grounding calculation."""

    def test_strong_grounding(self):
        """All symbols match = strong."""
        claim = {'target_symbols': ['foo', 'bar']}
        patch = """
-def foo(): pass
+def foo(): return 1
-def bar(): pass
+def bar(): return 2
"""
        result = calculate_grounding_strength(claim, patch)
        assert result.strength == 'strong'
        assert result.is_grounded is True
        assert result.matched_symbols == {'foo', 'bar'}
        assert result.unmatched_symbols == set()

    def test_weak_grounding(self):
        """Some symbols match = weak."""
        claim = {'target_symbols': ['foo', 'bar', 'baz']}
        patch = """
-def foo(): pass
+def foo(): return 1
"""
        result = calculate_grounding_strength(claim, patch)
        assert result.strength == 'weak'
        assert result.is_grounded is True
        assert 'foo' in result.matched_symbols
        assert 'bar' in result.unmatched_symbols
        assert 'baz' in result.unmatched_symbols

    def test_no_grounding(self):
        """No symbols match = none."""
        claim = {'target_symbols': ['foo', 'bar']}
        patch = """
-def baz(): pass
+def qux(): pass
"""
        result = calculate_grounding_strength(claim, patch)
        assert result.strength == 'none'
        assert result.is_grounded is False
        assert result.matched_symbols == set()
        assert result.unmatched_symbols == {'foo', 'bar'}

    def test_empty_target_symbols(self):
        """Claim with no target symbols = none."""
        claim = {'target_symbols': []}
        patch = "def foo(): pass"
        result = calculate_grounding_strength(claim, patch)
        assert result.strength == 'none'
        assert result.is_grounded is False


class TestFilterGroundedClaims:
    """Test filtering claims by grounding."""

    def test_filter_mixed_claims(self):
        """Should separate grounded from ungrounded claims."""
        claims = [
            {'claim_id': 'C1', 'target_symbols': ['foo']},
            {'claim_id': 'C2', 'target_symbols': ['bar']},
            {'claim_id': 'C3', 'target_symbols': ['baz']}
        ]
        patch = """
-def foo(): pass
+def foo(): return 1
-def bar(): pass
+def bar(): return 2
"""
        grounded, ungrounded = filter_grounded_claims(claims, patch)

        assert len(grounded) == 2
        assert len(ungrounded) == 1
        assert grounded[0]['claim_id'] == 'C1'
        assert grounded[1]['claim_id'] == 'C2'
        assert ungrounded[0]['claim_id'] == 'C3'

    def test_filter_with_strong_requirement(self):
        """Should filter by strong grounding when required."""
        claims = [
            {'claim_id': 'C1', 'target_symbols': ['foo']},          # strong
            {'claim_id': 'C2', 'target_symbols': ['foo', 'bar']},   # weak
            {'claim_id': 'C3', 'target_symbols': ['baz']},          # none
        ]
        patch = """
-def foo(): pass
+def foo(): return 1
"""
        grounded, ungrounded = filter_grounded_claims(
            claims, patch, min_strength='strong'
        )

        assert len(grounded) == 1
        assert len(ungrounded) == 2
        assert grounded[0]['claim_id'] == 'C1'

    def test_grounding_metadata_added(self):
        """Grounded claims should include grounding metadata."""
        claims = [
            {'claim_id': 'C1', 'target_symbols': ['foo']},
        ]
        patch = "-def foo(): pass\n+def foo(): return 1"

        grounded, _ = filter_grounded_claims(claims, patch)

        assert 'grounding' in grounded[0]
        assert grounded[0]['grounding']['is_grounded'] is True
        assert grounded[0]['grounding']['strength'] == 'strong'

    def test_empty_claims_list(self):
        """Should handle empty claims list."""
        grounded, ungrounded = filter_grounded_claims([], "def foo(): pass")
        assert grounded == []
        assert ungrounded == []


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    def test_django_issue_scenario(self):
        """Simulate a typical Django issue with multiple claims."""
        # Issue mentions multiple components, but only one is fixed
        claims = [
            {
                'claim_id': 'C1',
                'target_symbols': ['validate_email'],
                'claim_text': 'Email validation should handle plus signs'
            },
            {
                'claim_id': 'C2',
                'target_symbols': ['EmailField'],
                'claim_text': 'EmailField should use correct validator'
            },
            {
                'claim_id': 'C3',
                'target_symbols': ['User.save'],
                'claim_text': 'User model should validate on save'
            }
        ]

        # But the patch only touches validate_email
        patch = """
diff --git a/django/core/validators.py b/django/core/validators.py
-def validate_email(email):
-    return '@' in email
+def validate_email(email):
+    # Handle plus signs in email
+    return '@' in email and '+' not in email.split('@')[0]
"""

        grounded, ungrounded = filter_grounded_claims(claims, patch)

        # Only C1 should be grounded
        assert len(grounded) == 1
        assert grounded[0]['claim_id'] == 'C1'

        # C2 and C3 are not grounded
        assert len(ungrounded) == 2
        assert {c['claim_id'] for c in ungrounded} == {'C2', 'C3'}

    def test_complex_refactoring_scenario(self):
        """Test with a refactoring that touches multiple functions."""
        claims = [
            {'claim_id': 'C1', 'target_symbols': ['parse_input']},
            {'claim_id': 'C2', 'target_symbols': ['validate_input']},
            {'claim_id': 'C3', 'target_symbols': ['process_data']},
        ]

        patch = """
diff --git a/processor.py b/processor.py
-def parse_input(data):
+def parse_input(data):
     validated = validate_input(data)
-    return validated
+    return process_data(validated)

-def validate_input(data):
+def validate_input(data):
     return data.strip()

+def process_data(data):
+    return data.upper()
"""

        grounded, ungrounded = filter_grounded_claims(claims, patch)

        # All three claims should be grounded
        assert len(grounded) == 3
        assert len(ungrounded) == 0
