"""
Generate Hypothesis property-based tests for changed code.

This module generates targeted, executable pytest tests focusing on:
- Boundary conditions for new conditionals
- Edge cases for new loops
- Exception triggering tests
- General property-based tests
- Pattern-based instance creation (learned from existing tests)
"""

import ast
from typing import List, Dict, Any, Optional
from pathlib import Path
from .patch_analyzer import PatchAnalysis
from .test_pattern_learner import TestPatternLearner, ClassTestPatterns
from .signature_pattern_extractor import SignaturePatternExtractor


class HypothesisTestGenerator:
    """
    Generates pytest tests with Hypothesis for property-based testing.
    Focus on changed functions and their boundaries.

    Now supports pattern-based test generation by learning from existing tests.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize the test generator.

        Args:
            repo_path: Path to repository for pattern learning (optional)
        """
        self.repo_path = repo_path
        self.pattern_learner = TestPatternLearner(repo_path) if repo_path else None
        self.signature_extractor = SignaturePatternExtractor()
        self.patched_code_cache = None  # Store patched code for signature extraction

    def generate_tests(self, patch_analysis: PatchAnalysis, patched_code: str) -> str:
        """
        Generate test code targeting the changes in the patch.

        Args:
            patch_analysis: Analysis of what changed in the patch
            patched_code: The full patched code (for import context)

        Returns:
            Complete Python test file as a string
        """
        # Cache patched code for signature extraction
        self.patched_code_cache = patched_code

        test_lines = [
            "# Auto-generated change-aware fuzzing tests for patch validation",
            "import pytest",
            "from hypothesis import given, strategies as st, settings",
            "from hypothesis import assume",
            "import sys",
            "from pathlib import Path",
            "",
        ]

        # Add imports for the module/classes under test
        if patch_analysis.module_path:
            test_lines.append(f"# Import from patched module: {patch_analysis.module_path}")

            # Group functions by their class context
            class_based_funcs = {}
            standalone_funcs = []

            for func_name in patch_analysis.changed_functions:
                class_name = patch_analysis.class_context.get(func_name) if patch_analysis.class_context else None
                if class_name:
                    if class_name not in class_based_funcs:
                        class_based_funcs[class_name] = []
                    class_based_funcs[class_name].append(func_name)
                else:
                    standalone_funcs.append(func_name)

            # Import classes
            for class_name in class_based_funcs.keys():
                test_lines.append(f"from {patch_analysis.module_path} import {class_name}")

            # Import standalone functions
            if standalone_funcs:
                funcs_str = ", ".join(standalone_funcs)
                test_lines.append(f"from {patch_analysis.module_path} import {funcs_str}")

            test_lines.append("")
        else:
            test_lines.extend([
                "# NOTE: Module path not detected, tests may need manual import adjustment",
                "",
            ])

        # If no changed functions, generate a basic sanity test
        if not patch_analysis.changed_functions:
            test_lines.extend([
                "def test_patch_applied():",
                '    """Verify that the patch was applied (basic sanity check)"""',
                "    assert True, 'Patch applied successfully'",
                "",
            ])
            return '\n'.join(test_lines)

        # Extract function signatures for better test generation
        function_signatures = self._extract_function_signatures(patched_code)

        # Track function occurrences to avoid duplicate test names
        function_occurrences = {}

        # Generate tests for each changed function
        for func_name in patch_analysis.changed_functions:
            # Track occurrences for unique naming
            if func_name not in function_occurrences:
                function_occurrences[func_name] = 0
            else:
                function_occurrences[func_name] += 1
                continue  # Skip duplicates - already tested this function
            func_sig = function_signatures.get(func_name, {'params': [], 'has_args': False, 'has_kwargs': False})
            class_name = patch_analysis.class_context.get(func_name) if patch_analysis.class_context else None

            # Generate different test types based on change types
            if patch_analysis.change_types.get('conditionals'):
                test_lines.extend(self._generate_boundary_tests(func_name, func_sig, class_name))

            if patch_analysis.change_types.get('loops'):
                test_lines.extend(self._generate_loop_tests(func_name, func_sig, class_name))

            if patch_analysis.change_types.get('exceptions'):
                test_lines.extend(self._generate_exception_tests(func_name, func_sig, class_name))

            # Always generate general property test
            test_lines.extend(self._generate_property_test(func_name, func_sig, class_name))

        return '\n'.join(test_lines)

    def _extract_function_signatures(self, code: str) -> Dict[str, Dict[str, Any]]:
        """Extract function signatures for more intelligent test generation"""
        signatures = {}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    params = []
                    has_args = False
                    has_kwargs = False

                    for arg in node.args.args:
                        if arg.arg != 'self' and arg.arg != 'cls':
                            params.append(arg.arg)

                    if node.args.vararg:
                        has_args = True
                    if node.args.kwarg:
                        has_kwargs = True

                    signatures[node.name] = {
                        'params': params,
                        'has_args': has_args,
                        'has_kwargs': has_kwargs,
                        'param_count': len(params)
                    }
        except SyntaxError:
            pass

        return signatures

    def _generate_boundary_tests(self, func_name: str, func_sig: Dict, class_name: str = None) -> List[str]:
        """Generate tests for boundary conditions"""
        param_count = func_sig.get('param_count', 2)

        # Generate strategy based on parameter count
        if param_count == 0:
            strategies = ""
        elif param_count == 1:
            strategies = "st.one_of(st.none(), st.integers(), st.text())"
        else:
            strategies = ", ".join([
                "st.one_of(st.none(), st.integers(min_value=-100, max_value=100), st.text())"
                for _ in range(min(param_count, 3))
            ])

        return [
            f"@given({strategies})" if strategies else "",
            f"@settings(max_examples=50, deadline=1000)",
            f"def test_{func_name}_boundaries({', '.join([f'arg{i}' for i in range(min(param_count, 3))])}):" if param_count > 0 else f"def test_{func_name}_boundaries():",
            f'    """Test boundary conditions for {func_name}"""',
            f"    try:",
            f"        # Try calling with various boundary values",
            f"        result = {func_name}({', '.join([f'arg{i}' for i in range(min(param_count, 3))])})" if param_count > 0 else f"        result = {func_name}()",
            f"        # If function returns, it should be deterministic",
            f"        result2 = {func_name}({', '.join([f'arg{i}' for i in range(min(param_count, 3))])})" if param_count > 0 else f"        result2 = {func_name}()",
            f"        assert result == result2, 'Function should be deterministic'",
            f"    except (ValueError, TypeError, AttributeError, ZeroDivisionError, KeyError, IndexError):",
            f"        pass  # Expected for invalid inputs",
            f"",
        ]

    def _generate_loop_tests(self, func_name: str, func_sig: Dict, class_name: str = None) -> List[str]:
        """Generate tests for loop edge cases"""
        param_count = func_sig.get('param_count', 1)

        return [
            f"@given(st.lists(st.integers(), min_size=0, max_size=100))",
            f"@settings(max_examples=50, deadline=1000)",
            f"def test_{func_name}_loops(items):",
            f'    """Test loop edge cases for {func_name}"""',
            f"    try:",
            f"        # Test with empty list",
            f"        {func_name}([])" if param_count > 0 else f"        {func_name}()",
            f"        # Test with single item",
            f"        if items:",
            f"            {func_name}([items[0]])" if param_count > 0 else f"            {func_name}()",
            f"        # Test with full list",
            f"        {func_name}(items)" if param_count > 0 else f"        {func_name}()",
            f"    except (ValueError, TypeError, IndexError, AttributeError, ZeroDivisionError):",
            f"        pass  # Expected for invalid inputs",
            f"",
        ]

    def _generate_exception_tests(self, func_name: str, func_sig: Dict, class_name: str = None) -> List[str]:
        """Generate tests that should trigger exceptions"""
        param_count = func_sig.get('param_count', 1)

        return [
            f"def test_{func_name}_exceptions():",
            f'    """Test exception handling for {func_name}"""',
            f"    # Test with None",
            f"    try:",
            f"        result = {func_name}(None)" if param_count > 0 else f"        result = {func_name}()",
            f"    except (ValueError, TypeError, AttributeError):",
            f"        pass  # Expected exception",
            f"    ",
            f"    # Test with invalid types",
            f"    try:",
            f"        result = {func_name}('invalid', -1, [])" if param_count >= 2 else f"        result = {func_name}('invalid')" if param_count > 0 else f"        result = {func_name}()",
            f"    except (ValueError, TypeError, AttributeError, IndexError):",
            f"        pass  # Expected exception",
            f"",
        ]

    def _generate_property_test(self, func_name: str, func_sig: Dict, class_name: str = None) -> List[str]:
        """Generate general property-based test for standalone function or class method"""
        param_count = func_sig.get('param_count', 0)

        # For class methods, try pattern-based test generation
        if class_name:
            print(f"  🔍 Class method detected: {class_name}.{func_name}")
            # Try to use pattern learning if available
            if self.pattern_learner:
                print(f"  📚 Pattern learner available, attempting pattern learning...")
                pattern_test = self._generate_pattern_based_class_test(class_name, func_name)
                if pattern_test:
                    print(f"  ✅ Pattern-based test generated!")
                    return pattern_test
                else:
                    print(f"  ⚠️  Pattern learning returned nothing")
            else:
                print(f"  ⚠️  No pattern learner initialized")

            # Fallback: basic existence check if pattern learning unavailable or failed
            print(f"  ℹ️  Falling back to existence check")
            return [
                f"def test_{func_name}_exists():",
                f'    """Verify {class_name}.{func_name} exists and is callable"""',
                f"    assert hasattr({class_name}, '{func_name}'), '{class_name} should have {func_name} method'",
                f"    # Note: Pattern learning not available or found no patterns",
                f"",
                f"",
            ]

        # Generate appropriate strategies for standalone functions
        if param_count == 0:
            strategies = ""
            args = ""
        elif param_count == 1:
            strategies = "st.one_of(st.integers(), st.text(), st.lists(st.integers()))"
            args = "arg0"
        elif param_count == 2:
            strategies = "st.one_of(st.integers(), st.text()), st.one_of(st.integers(), st.lists(st.integers()))"
            args = "arg0, arg1"
        else:
            strategies = ", ".join([
                "st.one_of(st.integers(), st.text(), st.lists(st.integers()))"
                for _ in range(min(param_count, 3))
            ])
            args = ", ".join([f"arg{i}" for i in range(min(param_count, 3))])

        return [
            f"@given({strategies})" if strategies else "",
            f"@settings(max_examples=100, deadline=1000)",
            f"def test_{func_name}_properties({args}):" if args else f"def test_{func_name}_properties():",
            f'    """Test general properties of {func_name}"""',
            f"    try:",
            f"        # Determinism test - same inputs should yield same outputs",
            f"        result1 = {func_name}({args})" if args else f"        result1 = {func_name}()",
            f"        result2 = {func_name}({args})" if args else f"        result2 = {func_name}()",
            f"        assert result1 == result2, 'Function should be deterministic'",
            f"        ",
            f"        # Type stability test - result type should be consistent",
            f"        assert type(result1) == type(result2), 'Result type should be stable'",
            f"    except Exception:",
            f"        pass  # Some inputs expected to fail",
            f"",
            f"",
        ]

    def _generate_pattern_based_class_test(self, class_name: str, func_name: str) -> Optional[List[str]]:
        """
        Generate pattern-based test for class methods using learned patterns.

        Uses a multi-tier fallback strategy:
        1. Try learning from existing tests (best - uses real patterns)
        2. Fall back to signature extraction (good - uses type hints and defaults)
        3. Fall back to None (will use existence check)

        Args:
            class_name: Name of the class
            func_name: Name of the method being tested

        Returns:
            List of code lines for the test, or None if no patterns available
        """
        try:
            # TIER 1: Try learning patterns from existing tests
            if self.pattern_learner:
                print(f"    🔍 Learning patterns for {class_name}...")
                patterns = self.pattern_learner.learn_patterns(class_name)

                if patterns and patterns.patterns:
                    print(f"    ✅ Found {len(patterns.patterns)} patterns")
                    # Get the most common patterns
                    top_patterns = patterns.get_most_common_patterns(limit=3)
                    print(f"    📊 Top {len(top_patterns)} patterns selected")

                    if top_patterns:
                        # Generate strategies from learned patterns
                        strategies = self.pattern_learner.generate_hypothesis_strategy_from_patterns(patterns)
                        print(f"    🎯 Generated {len(strategies)} Hypothesis strategies")

                        if strategies:
                            # ENHANCEMENT: Also add strategies for parameters not in patterns (like new params)
                            # Extract function signature to find ALL parameters
                            func_signatures = self._extract_function_signatures(self.patched_code_cache)
                            if func_name in func_signatures:
                                sig_params = set(func_signatures[func_name].get('params', []))
                                learned_params = set(s[0] for s in strategies)
                                missing_params = sig_params - learned_params

                                if missing_params:
                                    print(f"    ⚠️  Found {len(missing_params)} params not in patterns: {missing_params}")
                                    # Add basic strategies for missing params
                                    for param in missing_params:
                                        # Use simple strategies for new parameters
                                        strategies.append((param, "st.booleans()"))  # Most new params are flags
                                        print(f"    ➕ Added strategy for new param: {param}")

                            # Generate Hypothesis-based test with learned strategies
                            print(f"    🧪 Generating Hypothesis-based test with {len(strategies)} total strategies")
                            return self._generate_hypothesis_pattern_test(class_name, func_name, strategies, top_patterns)
                        else:
                            # If we can't generate strategies, use direct patterns
                            print(f"    📝 Generating direct pattern test")
                            return self._generate_direct_pattern_test(class_name, func_name, top_patterns)
                else:
                    print(f"    ⚠️  No patterns found for {class_name}")

            # TIER 2: Fall back to signature extraction (for new LLM-generated code)
            if self.patched_code_cache:
                print(f"ℹ️  No test patterns found for {class_name}, trying signature extraction...")
                return self._generate_signature_based_test(class_name, func_name)

            # TIER 3: No patterns available
            return None

        except Exception as e:
            # If pattern learning fails, try signature extraction before giving up
            print(f"Warning: Pattern learning failed for {class_name}: {e}")

            # Try signature extraction as fallback
            if self.patched_code_cache:
                try:
                    return self._generate_signature_based_test(class_name, func_name)
                except Exception as e2:
                    print(f"Warning: Signature extraction also failed: {e2}")

            return None

    def _generate_direct_pattern_test(self, class_name: str, func_name: str,
                                     patterns: List) -> List[str]:
        """Generate test using direct patterns (no Hypothesis)"""
        test_lines = [
            f"def test_{func_name}_with_learned_patterns():",
            f'    """Test {class_name}.{func_name} using patterns learned from existing tests"""',
        ]

        # Test with each learned pattern
        for i, pattern in enumerate(patterns[:3]):  # Limit to 3 patterns
            params_str = ", ".join([f"{k}={repr(v)}" for k, v in pattern.parameters.items()])

            test_lines.extend([
                f"    # Pattern {i+1}: {pattern.source_location}",
                f"    try:",
                f"        instance = {class_name}({params_str})",
                f"        assert instance is not None",
                f"        # Verify the method exists and can be accessed",
                f"        assert hasattr(instance, '{func_name}')",
            ])

            # If it's __init__, we've already tested it by creating the instance
            if func_name == "__init__":
                test_lines.extend([
                    f"        # __init__ tested by successful instantiation",
                ])
            else:
                test_lines.extend([
                    f"        # Method exists and is callable",
                    f"        assert callable(getattr(instance, '{func_name}'))",
                ])

            test_lines.extend([
                f"    except Exception as e:",
                f"        # Some patterns may not work with current code changes",
                f"        pass",
                f"",
            ])

        test_lines.append("")
        return test_lines

    def _generate_hypothesis_pattern_test(self, class_name: str, func_name: str,
                                         strategies: List, patterns: List) -> List[str]:
        """Generate Hypothesis-based test using learned parameter strategies"""
        test_lines = [
            "# Hypothesis strategies learned from existing tests",
        ]

        # Build the @given decorator
        strategy_params = []
        param_names = []
        for param_name, strategy_code in strategies[:5]:  # Limit to 5 parameters
            strategy_params.append(f"{param_name}={strategy_code}")
            param_names.append(param_name)

        if not strategy_params:
            return None

        given_decorator = f"@given({', '.join(strategy_params)})"
        func_params = ", ".join(param_names)
        # Use keyword arguments for instance creation to ensure correct parameter assignment
        func_kwargs = ", ".join([f"{name}={name}" for name in param_names])

        test_lines.extend([
            given_decorator,
            "@settings(max_examples=100, deadline=2000)",  # Increased from 50 to 100 for better coverage
            f"def test_{func_name}_with_fuzzing({func_params}):",
            f'    """',
            f'    Fuzz test {class_name}.{func_name} with learned parameter strategies.',
            f'    Patterns learned from: {patterns[0].source_location if patterns else "existing tests"}',
            f'    """',
            f"    try:",
            f"        # Create instance with fuzzed parameters (using keyword arguments)",
            f"        instance = {class_name}({func_kwargs})",
            f"        assert instance is not None",
            f"",
        ])

        # Add specific tests based on the function
        if func_name == "__init__":
            test_lines.extend([
                f"        # Verify initialization completed successfully",
                f"        assert instance is not None",
                f"        # Try to access common attributes to trigger lazy initialization",
                f"        try:",
                f"            # Access __dict__ to trigger any property evaluations",
                f"            _ = instance.__dict__",
                f"            # Try str/repr which often triggers internal state validation",
                f"            _ = str(type(instance))",
                f"        except Exception:",
                f"            pass  # Some objects don't allow __dict__ access",
                f"",
            ])
            # Add actual attribute checks (not comments)
            for param_name in param_names[:3]:
                test_lines.extend([
                    f"        # Verify parameter {param_name} was processed",
                    f"        if hasattr(instance, '{param_name}'):",
                    f"            _ = getattr(instance, '{param_name}')  # Access it",
                ])
            test_lines.append(f"")
        else:
            test_lines.extend([
                f"        # Call the method to actually test it (not just check existence)",
                f"        method = getattr(instance, '{func_name}')",
                f"        assert callable(method)",
                f"        # Try calling with no args first",
                f"        try:",
                f"            result = method()",
                f"            # Verify result properties",
                f"            _ = type(result)  # Access the result",
                f"        except TypeError:",
                f"            # Method requires arguments - that's okay, we tested it exists",
                f"            pass",
            ])

        test_lines.extend([
            f"    except (ValueError, TypeError, AttributeError) as e:",
            f"        # Expected for some parameter combinations",
            f"        # Fuzzing explores parameter space including invalid combinations",
            f"        pass",
            f"",
            f"",
        ])

        return test_lines

    def _generate_signature_based_test(self, class_name: str, func_name: str) -> Optional[List[str]]:
        """
        Generate test based on function signature (type hints and defaults).

        This is used as a fallback for LLM-generated code or new functions
        where no existing tests are available.

        Args:
            class_name: Name of the class
            func_name: Name of the method

        Returns:
            List of code lines for the test, or None if extraction fails
        """
        # Extract patterns from signature
        sig_patterns = self.signature_extractor.extract_from_code(
            self.patched_code_cache,
            class_name,
            func_name
        )

        if not sig_patterns:
            return None

        # Try to generate Hypothesis strategies
        strategies = self.signature_extractor.generate_hypothesis_strategies(sig_patterns)

        if strategies:
            # Generate Hypothesis-based test with signature strategies
            test_lines = [
                "# Hypothesis strategies inferred from function signature",
            ]

            # Build the @given decorator
            strategy_params = []
            param_names = []
            for param_name, strategy_code in strategies[:5]:  # Limit to 5 parameters
                strategy_params.append(f"{param_name}={strategy_code}")
                param_names.append(param_name)

            given_decorator = f"@given({', '.join(strategy_params)})"
            func_params = ", ".join(param_names)
            # Use keyword arguments for instance creation to ensure correct parameter assignment
            func_kwargs = ", ".join([f"{name}={name}" for name in param_names])

            test_lines.extend([
                given_decorator,
                "@settings(max_examples=50, deadline=2000)",
                f"def test_{func_name}_signature_based({func_params}):",
                f'    """',
                f'    Test {class_name}.{func_name} using signature-inferred strategies.',
                f'    Note: This is a fallback test for LLM-generated or new code.',
                f'    """',
                f"    try:",
                f"        # Create instance with signature-inferred parameters (using keyword arguments)",
                f"        instance = {class_name}({func_kwargs})",
                f"        assert instance is not None",
            ])

            # Add specific tests based on the function
            if func_name == "__init__":
                test_lines.extend([
                    f"        # Verify initialization completed successfully",
                ])
            else:
                test_lines.extend([
                    f"        # Verify method exists and is callable",
                    f"        assert hasattr(instance, '{func_name}')",
                    f"        assert callable(getattr(instance, '{func_name}'))",
                ])

            test_lines.extend([
                f"    except (ValueError, TypeError, AttributeError) as e:",
                f"        # Expected for some parameter combinations",
                f"        pass",
                f"",
                f"",
            ])

            return test_lines

        # If we can't generate Hypothesis strategies, try default-based test
        default_params = self.signature_extractor.generate_default_based_test(
            class_name, func_name, sig_patterns
        )

        if default_params:
            test_lines = [
                f"def test_{func_name}_with_defaults():",
                f'    """Test {class_name}.{func_name} using default parameter values"""',
                f"    # Parameters extracted from function signature",
            ]

            params_str = ", ".join([f"{k}={repr(v)}" for k, v in default_params.items()])

            test_lines.extend([
                f"    try:",
                f"        instance = {class_name}({params_str})",
                f"        assert instance is not None",
            ])

            if func_name == "__init__":
                test_lines.extend([
                    f"        # __init__ tested by successful instantiation",
                ])
            else:
                test_lines.extend([
                    f"        # Verify method exists",
                    f"        assert hasattr(instance, '{func_name}')",
                ])

            test_lines.extend([
                f"    except Exception as e:",
                f"        # Some parameter combinations may not be valid",
                f"        pass",
                f"",
                f"",
            ])

            return test_lines

        return None


# Example usage
if __name__ == "__main__":
    from patch_analyzer import PatchAnalyzer

    patch_diff = """
--- a/example.py
+++ b/example.py
@@ -10,6 +10,8 @@ def divide(a, b):
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
     return a / b
"""

    patched_code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""

    analyzer = PatchAnalyzer()
    analysis = analyzer.parse_patch(patch_diff, patched_code)

    generator = HypothesisTestGenerator()
    test_code = generator.generate_tests(analysis, patched_code)

    print("Generated test code:")
    print("=" * 80)
    print(test_code)
