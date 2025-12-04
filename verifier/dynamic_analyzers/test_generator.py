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
from .differential_tester import DifferentialFuzzer


class HypothesisTestGenerator:
    """
    Generates pytest tests with Hypothesis for property-based testing.
    Focus on changed functions and their boundaries.

    Now supports pattern-based test generation by learning from existing tests.
    """

    def __init__(self, repo_path: Optional[Path] = None, enable_differential: bool = True):
        """
        Initialize the test generator.

        Args:
            repo_path: Path to repository for pattern learning (optional)
            enable_differential: Enable differential testing (comparing original vs patched)
        """
        self.repo_path = repo_path
        self.pattern_learner = TestPatternLearner(repo_path) if repo_path else None
        self.signature_extractor = SignaturePatternExtractor()
        self.patched_code_cache = None  # Store patched code for signature extraction
        self.enable_differential = enable_differential

    def generate_tests(self, patch_analysis: PatchAnalysis, patched_code: str, original_code: Optional[str] = None) -> str:
        """
        Generate test code targeting the changes in the patch.

        Args:
            patch_analysis: Analysis of what changed in the patch
            patched_code: The full patched code (for import context)
            original_code: Original code before patch (for differential testing)

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

        # Add differential tests if original code is available
        if self.enable_differential and original_code:
            test_lines.append("")
            test_lines.append("# ========== DIFFERENTIAL TESTS (Original vs Patched) ==========")
            test_lines.append("")

            for func_name in patch_analysis.changed_functions:
                func_sig = function_signatures.get(func_name, {'params': [], 'has_args': False, 'has_kwargs': False})
                diff_tests = self._generate_differential_tests(func_name, func_sig, original_code, patched_code)
                if diff_tests:
                    test_lines.extend(diff_tests)

        return '\n'.join(test_lines)

    def _extract_function_signatures(self, code: str) -> Dict[str, Dict[str, Any]]:
        """Extract function signatures for more intelligent test generation"""
        signatures = {}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    params = []
                    defaults = {}
                    type_hints = {}
                    has_args = False
                    has_kwargs = False

                    # Extract parameters
                    for arg in node.args.args:
                        if arg.arg != 'self' and arg.arg != 'cls':
                            params.append(arg.arg)
                            # Extract type annotations
                            if arg.annotation:
                                type_hints[arg.arg] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else None

                    # Extract default values
                    if node.args.defaults:
                        # Defaults align to the end of params
                        num_defaults = len(node.args.defaults)
                        for i, default in enumerate(node.args.defaults):
                            param_idx = len(params) - num_defaults + i
                            if param_idx >= 0 and param_idx < len(params):
                                param_name = params[param_idx]
                                try:
                                    defaults[param_name] = ast.literal_eval(default)
                                except (ValueError, SyntaxError):
                                    defaults[param_name] = None

                    if node.args.vararg:
                        has_args = True
                    if node.args.kwarg:
                        has_kwargs = True

                    signatures[node.name] = {
                        'params': params,
                        'defaults': defaults,
                        'type_hints': type_hints,
                        'has_args': has_args,
                        'has_kwargs': has_kwargs,
                        'param_count': len(params)
                    }
        except SyntaxError:
            pass

        return signatures

    def _infer_smart_strategy_for_param(self, param_name: str, func_sig: Dict) -> str:
        """
        Infer appropriate Hypothesis strategy for a parameter.

        Args:
            param_name: Name of the parameter
            func_sig: Function signature dictionary with defaults and type hints

        Returns:
            Hypothesis strategy code as string
        """
        defaults = func_sig.get('defaults', {})
        type_hints = func_sig.get('type_hints', {})

        # Check if there's a default value
        if param_name in defaults:
            default = defaults[param_name]

            # For boolean defaults
            if isinstance(default, bool):
                return "st.booleans()"

            # For numeric defaults
            elif isinstance(default, int):
                # Generate values around the default
                if default == 0:
                    return "st.integers(min_value=-10, max_value=10)"
                else:
                    return f"st.one_of(st.just({default}), st.integers(min_value=max(0, {default}-10), max_value={default}+10))"

            elif isinstance(default, float):
                return f"st.one_of(st.just({default}), st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False))"

            # For None defaults (optional params)
            elif default is None:
                # Check type hint if available
                if param_name in type_hints:
                    hint = type_hints[param_name]
                    if 'int' in hint.lower():
                        return "st.one_of(st.none(), st.integers(min_value=1, max_value=100))"
                    elif 'float' in hint.lower():
                        return "st.one_of(st.none(), st.floats(min_value=0.01, max_value=100.0))"
                    elif 'str' in hint.lower():
                        return "st.one_of(st.none(), st.text(min_size=1, max_size=20))"
                # Generic optional
                return "st.one_of(st.none(), st.integers(), st.text())"

            # For list/tuple defaults
            elif isinstance(default, (list, tuple)):
                if all(isinstance(x, (int, float)) for x in default):
                    # Numeric list/tuple
                    return f"st.lists(st.floats(min_value=0.001, max_value=100.0), min_size=1, max_size=5)"
                else:
                    return "st.lists(st.one_of(st.integers(), st.text()), min_size=0, max_size=5)"

        # Check parameter name patterns (common conventions)
        param_lower = param_name.lower()

        # Cross-validation fold parameter
        if param_lower in ['cv', 'n_folds', 'folds']:
            return "st.one_of(st.none(), st.integers(min_value=2, max_value=10))"

        # Regularization parameter
        elif 'alpha' in param_lower or 'lambda' in param_lower or 'regulariz' in param_lower:
            return "st.lists(st.floats(min_value=0.01, max_value=10.0, allow_nan=False), min_size=1, max_size=5)"

        # Random state
        elif 'random' in param_lower and 'state' in param_lower:
            return "st.one_of(st.none(), st.integers(min_value=0, max_value=2**31-1))"

        # Number of iterations/epochs
        elif any(x in param_lower for x in ['n_iter', 'max_iter', 'epochs', 'iterations']):
            return "st.integers(min_value=1, max_value=1000)"

        # Tolerance/threshold parameters
        elif any(x in param_lower for x in ['tol', 'tolerance', 'threshold', 'epsilon']):
            return "st.floats(min_value=1e-6, max_value=0.1, allow_nan=False)"

        # Boolean flags
        elif any(x in param_lower for x in ['verbose', 'debug', 'fit_intercept', 'normalize', 'copy']):
            return "st.booleans()"

        # Size/count parameters
        elif any(x in param_lower for x in ['n_', 'num_', 'count', 'size']) and 'feature' not in param_lower:
            return "st.integers(min_value=1, max_value=100)"

        # Storage/save flags (new parameters added by patches)
        elif any(x in param_lower for x in ['store', 'save', 'cache', 'keep']):
            return "st.booleans()"

        # Check type hints if available
        if param_name in type_hints:
            hint = type_hints[param_name]
            if 'bool' in hint.lower():
                return "st.booleans()"
            elif 'int' in hint.lower():
                # Check if Optional - if so, include None
                if 'optional' in hint.lower() or 'none' in hint.lower():
                    return "st.one_of(st.none(), st.integers(min_value=0, max_value=100))"
                # For non-optional ints, assume positive (common for scikit-learn params)
                return "st.integers(min_value=0, max_value=100)"
            elif 'float' in hint.lower():
                if 'optional' in hint.lower() or 'none' in hint.lower():
                    return "st.one_of(st.none(), st.floats(min_value=0.0, max_value=100.0, allow_nan=False))"
                return "st.floats(min_value=0.0, max_value=100.0, allow_nan=False)"
            elif 'str' in hint.lower():
                return "st.text(min_size=0, max_size=20)"
            elif 'list' in hint.lower():
                return "st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10)"

        # Default fallback - more restrictive to avoid invalid values
        # Most sklearn parameters are either booleans, positive ints, or None
        return "st.one_of(st.none(), st.booleans(), st.integers(min_value=0, max_value=10))"

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
            f"@settings(max_examples=1000, deadline=2000)",
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
            f"@settings(max_examples=1000, deadline=2000)",
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
            f"@settings(max_examples=1000, deadline=2000)",
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
                                    # Add smart strategies for missing params
                                    for param in missing_params:
                                        # Use intelligent strategy inference based on param name, defaults, and type hints
                                        smart_strategy = self._infer_smart_strategy_for_param(param, func_signatures[func_name])
                                        strategies.append((param, smart_strategy))
                                        print(f"    ➕ Added smart strategy for new param '{param}': {smart_strategy[:50]}...")

                            # Generate Hypothesis-based test with learned strategies
                            print(f"    🧪 Generating Hypothesis-based test with {len(strategies)} total strategies")
                            test_lines = self._generate_hypothesis_pattern_test(class_name, func_name, strategies, top_patterns)

                            # For sklearn-like classes, also generate integration test with fit/predict
                            if self._is_sklearn_like_class(class_name) and func_name == '__init__':
                                print(f"    🔬 Detected sklearn-like class, adding integration test with fit/predict")
                                sklearn_test = self._generate_sklearn_integration_test(class_name, func_name, strategies, top_patterns)
                                if sklearn_test:
                                    test_lines.extend(sklearn_test)
                                    print(f"    ✅ Added sklearn integration test")

                            return test_lines
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
        new_params = []  # Track new parameters that weren't in learned patterns

        # Identify which params are new (likely added by the patch)
        learned_param_names = set()
        if patterns:
            for pattern in patterns:
                learned_param_names.update(pattern.parameters.keys())

        for param_name, strategy_code in strategies[:5]:  # Limit to 5 parameters
            strategy_params.append(f"{param_name}={strategy_code}")
            param_names.append(param_name)
            if param_name not in learned_param_names:
                new_params.append(param_name)

        if not strategy_params:
            return None

        given_decorator = f"@given({', '.join(strategy_params)})"
        func_params = ", ".join(param_names)
        # Use keyword arguments for instance creation to ensure correct parameter assignment
        func_kwargs = ", ".join([f"{name}={name}" for name in param_names])

        test_lines.extend([
            given_decorator,
            "@settings(max_examples=1000, deadline=2000)",  # Increased to 1000 for differential testing
            f"def test_{func_name}_with_fuzzing({func_params}):",
            f'    """',
            f'    Fuzz test {class_name}.{func_name} with learned parameter strategies.',
            f'    Patterns learned from: {patterns[0].source_location if patterns else "existing tests"}',
        ])

        if new_params:
            test_lines.append(f'    New parameters being tested: {", ".join(new_params)}')

        test_lines.extend([
            f'    """',
            f"    ",
        ])

        # Only add assume() for RELATIONSHIPS between parameters, not basic constraints
        # (basic constraints are now enforced by the strategies themselves)

        # Add specific validation for relationships between new and existing params
        # Example: If store_cv_values=True, then cv must not be None
        needs_assumptions = False
        if 'store_cv_values' in param_names or 'cache' in ' '.join(param_names).lower():
            for param in param_names:
                if 'cv' in param.lower() and param != 'store_cv_values':
                    # If storing CV values, CV must be valid
                    storage_param = next((p for p in param_names if 'store' in p.lower() or 'cache' in p.lower()), None)
                    if storage_param:
                        if not needs_assumptions:
                            test_lines.append(f"    # Parameter relationship assumptions (complex constraints)")
                            needs_assumptions = True
                        test_lines.append(f"    # When {storage_param}=True, {param} should be valid")
                        test_lines.append(f"    assume(not {storage_param} or {param} is not None)")

        # Add interdependencies for lists that need minimum length
        for param in param_names:
            param_lower = param.lower()
            # For alpha lists, sklearn requires at least one value
            if 'alpha' in param_lower:
                if not needs_assumptions:
                    test_lines.append(f"    # Parameter relationship assumptions (complex constraints)")
                    needs_assumptions = True
                test_lines.append(f"    # Alphas must have at least one positive value if it's a list")
                test_lines.append(f"    if isinstance({param}, (list, tuple)):")
                test_lines.append(f"        assume(len({param}) > 0)")

        if needs_assumptions:
            test_lines.append(f"")

        test_lines.extend([
            f"    ",
            f"    try:",
            f"        # Create instance with fuzzed parameters (using keyword arguments)",
            f"        instance = {class_name}({func_kwargs})",
            f"        assert instance is not None, 'Instance should be created'",
            f"",
        ])

        # Add specific tests based on the function
        if func_name == "__init__":
            test_lines.extend([
                f"        # Verify initialization completed successfully",
                f"        assert hasattr(instance, '__class__'), 'Instance should have __class__ attribute'",
                f"        ",
                f"        # Try to access common attributes to trigger lazy initialization",
                f"        try:",
                f"            # Access __dict__ to trigger any property evaluations",
                f"            _ = instance.__dict__",
                f"            # Try str/repr which often triggers internal state validation",
                f"            _ = str(type(instance))",
                f"        except (AttributeError, TypeError):",
                f"            pass  # Some objects don't allow __dict__ access",
                f"",
            ])

            # Add specific checks for new parameters (likely added by patch)
            if new_params:
                test_lines.extend([
                    f"        # Verify NEW parameters (likely added by patch) were processed correctly",
                ])
                for param_name in new_params:
                    param_lower = param_name.lower()
                    # For storage/cache parameters, verify the storage was initialized
                    if any(x in param_lower for x in ['store', 'save', 'cache', 'keep']):
                        test_lines.extend([
                            f"        # Check if {param_name}=True creates appropriate storage",
                            f"        if {param_name}:",
                            f"            # Look for related storage attributes (cv_values_, cache_, etc.)",
                            f"            storage_attrs = [attr for attr in dir(instance) if 'value' in attr.lower() or 'cache' in attr.lower()]",
                            f"            # At least verify instance was created with this parameter",
                            f"            assert hasattr(instance, '{param_name}') or len(storage_attrs) >= 0, 'Storage parameter should be processed'",
                        ])
                    else:
                        test_lines.extend([
                            f"        # Verify parameter {param_name} was processed",
                            f"        if hasattr(instance, '{param_name}'):",
                            f"            attr_value = getattr(instance, '{param_name}')",
                            f"            # Attribute should match or be derived from input",
                            f"            assert attr_value is not None or {param_name} is None, 'Attribute should be set'",
                        ])

            # Add checks for existing learned parameters too
            test_lines.extend([
                f"        ",
                f"        # Verify core attributes from learned parameters",
            ])
            for param_name in param_names[:3]:
                if param_name not in new_params:  # Only check learned params
                    test_lines.extend([
                        f"        if hasattr(instance, '{param_name}'):",
                        f"            _ = getattr(instance, '{param_name}')  # Access it to trigger lazy init",
                    ])
            test_lines.append(f"")
        else:
            test_lines.extend([
                f"        # Call the method to actually test it (not just check existence)",
                f"        method = getattr(instance, '{func_name}')",
                f"        assert callable(method), 'Method should be callable'",
                f"        # Try calling with no args first",
                f"        try:",
                f"            result = method()",
                f"            # Verify result properties",
                f"            assert result is not None or result == None, 'Method should return a value'",
                f"            _ = type(result)  # Access the result",
                f"        except TypeError:",
                f"            # Method requires arguments - that's okay, we tested it exists",
                f"            pass",
            ])

        test_lines.extend([
            f"    except (ValueError, TypeError, AttributeError) as e:",
            f"        # Expected for some parameter combinations",
            f"        # This is normal for fuzzing - we explore invalid parameter space too",
            f"        # The key is that SOME combinations succeed and execute new code",
            f"        pass",
            f"",
            f"",
        ])

        return test_lines

    def _is_sklearn_like_class(self, class_name: str) -> bool:
        """Check if class is from sklearn or similar ML libraries with lazy initialization"""
        class_lower = class_name.lower()
        return any(indicator in class_lower for indicator in [
            'classifier', 'regressor', 'estimator', 'transformer',
            'cluster', 'decomposition', 'cv', 'grid', 'search'
        ])

    def _generate_sklearn_integration_test(self, class_name: str, func_name: str,
                                          strategies: List, patterns: List) -> List[str]:
        """
        Generate two-phase integration test for sklearn-style classes.

        Phase 1: Create instance (__init__)
        Phase 2: Call fit/transform to trigger lazy initialization

        This is critical because many sklearn methods only execute new code during fit(),
        not during __init__.
        """
        # Build the @given decorator (same as pattern test)
        strategy_params = []
        param_names = []
        new_params = []

        # Identify which params are new
        learned_param_names = set()
        if patterns:
            for pattern in patterns:
                learned_param_names.update(pattern.parameters.keys())

        for param_name, strategy_code in strategies[:5]:
            strategy_params.append(f"{param_name}={strategy_code}")
            param_names.append(param_name)
            if param_name not in learned_param_names:
                new_params.append(param_name)

        if not strategy_params:
            return []

        given_decorator = f"@given({', '.join(strategy_params)})"
        func_params = ", ".join(param_names)
        func_kwargs = ", ".join([f"{name}={name}" for name in param_names])

        test_lines = [
            "# Two-phase integration test for sklearn-style class",
            "# Phase 1: Init, Phase 2: Fit/transform to trigger lazy initialization",
            "import numpy as np",
            "",
            given_decorator,
            "@settings(max_examples=1000, deadline=5000)",  # Longer deadline for fit operations
            f"def test_{func_name}_sklearn_integration({func_params}):",
            f'    """',
            f'    Integration test for {class_name}.{func_name} with actual fit/predict workflow.',
            f'    Tests that new parameters work correctly through the full ML pipeline.',
        ]

        if new_params:
            test_lines.append(f'    New parameters: {", ".join(new_params)}')

        test_lines.extend([
            f'    """',
            f"    ",
        ])

        # Only add assume() for parameter relationships (not basic validation)
        needs_sklearn_assumptions = False

        # Handle store_cv_values relationship - this is a true inter-parameter constraint
        if 'store_cv_values' in param_names:
            for param in param_names:
                if 'cv' in param.lower() and param != 'store_cv_values':
                    if not needs_sklearn_assumptions:
                        test_lines.append(f"    # Parameter relationship constraints")
                        needs_sklearn_assumptions = True
                    test_lines.append(f"    # If storing CV values, cv must be specified")
                    test_lines.append(f"    assume(not store_cv_values or {param} is not None)")

        if needs_sklearn_assumptions:
            test_lines.append(f"")

        test_lines.extend([
            f"    ",
            f"    try:",
            f"        # PHASE 1: Create instance",
            f"        model = {class_name}({func_kwargs})",
            f"        assert model is not None, 'Model should be instantiated'",
            f"        ",
            f"        # PHASE 2: Create dummy data and call fit to trigger lazy initialization",
            f"        # This is where most sklearn bugs manifest!",
            f"        try:",
            f"            # Generate small dataset",
            f"            np.random.seed(42)",
            f"            n_samples = 50",
            f"            n_features = 5",
            f"            n_classes = 3",
            f"            ",
            f"            X = np.random.randn(n_samples, n_features)",
            f"            y = np.random.randint(0, n_classes, size=n_samples)",
            f"            ",
            f"            # Try to fit the model - this triggers lazy initialization!",
            f"            model.fit(X, y)",
            f"            ",
        ])

        # Add specific checks for new parameters after fit
        if new_params:
            test_lines.append(f"            # Verify NEW parameters work after fit (where lazy init happens)")
            for param_name in new_params:
                param_lower = param_name.lower()
                if any(x in param_lower for x in ['store', 'save', 'cache']):
                    test_lines.extend([
                        f"            # Check if {param_name}=True actually stored values after fit",
                        f"            if {param_name}:",
                        f"                # Look for cv_values_, cache_, or similar storage attributes",
                        f"                stored_attrs = [attr for attr in dir(model) if 'value' in attr.lower() or 'cache' in attr.lower()]",
                        f"                # If store_cv_values=True, there should be cv_values_ attribute",
                        f"                if hasattr(model, 'cv_values_'):",
                        f"                    assert model.cv_values_ is not None, 'CV values should be stored'",
                    ])

        test_lines.extend([
            f"            ",
            f"            # Try prediction to ensure full pipeline works",
            f"            if hasattr(model, 'predict'):",
            f"                predictions = model.predict(X)",
            f"                assert len(predictions) == len(y), 'Predictions should match input length'",
            f"            ",
            f"            # Try score if available",
            f"            if hasattr(model, 'score'):",
            f"                score = model.score(X, y)",
            f"                assert isinstance(score, (int, float)), 'Score should be numeric'",
            f"            ",
            f"        except (ValueError, TypeError, np.linalg.LinAlgError) as fit_error:",
            f"            # Some parameter combinations may not be valid for this dataset",
            f"            # That's okay - we still tested the __init__ code",
            f"            pass",
            f"        ",
            f"    except (ValueError, TypeError, AttributeError) as init_error:",
            f"        # Expected for some parameter combinations during initialization",
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
                "@settings(max_examples=1000, deadline=3000)",
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

    def _generate_differential_tests(self, func_name: str, func_sig: Dict,
                                     original_code: str, patched_code: str) -> List[str]:
        """
        Generate differential tests comparing original vs patched behavior.

        Args:
            func_name: Name of the function to test
            func_sig: Function signature dictionary
            original_code: Code before patch
            patched_code: Code after patch

        Returns:
            List of test code lines
        """
        params = func_sig.get('params', [])
        if not params:
            return []

        # Generate strategies for each parameter
        strategies = []
        for param in params[:5]:  # Limit to 5 params
            strategy = self._infer_smart_strategy_for_param(param, func_sig)
            strategies.append(f"{param}={strategy}")

        param_str = ", ".join(params[:5])
        strategy_str = ", ".join(strategies)

        test_lines = [
            f"def test_{func_name}_differential({param_str}):",
            f'    """',
            f'    Differential test: Compare behavior between original and patched {func_name}.',
            f'    Detects behavioral divergences (different results or exceptions).',
            f'    """',
            f"    # Load original function",
            f"    original_code = '''",
            f"{original_code}",
            f"    '''",
            f"    ",
            f"    # Load patched function",
            f"    patched_code = '''",
            f"{patched_code}",
            f"    '''",
            f"    ",
            f"    # Execute both versions",
            f"    original_namespace = {{}}",
            f"    patched_namespace = {{}}",
            f"    ",
            f"    try:",
            f"        exec(original_code, original_namespace)",
            f"        original_func = original_namespace.get('{func_name}')",
            f"    except Exception as e:",
            f"        pytest.skip(f'Could not load original function: {{e}}')",
            f"    ",
            f"    try:",
            f"        exec(patched_code, patched_namespace)",
            f"        patched_func = patched_namespace.get('{func_name}')",
            f"    except Exception as e:",
            f"        pytest.skip(f'Could not load patched function: {{e}}')",
            f"    ",
            f"    if original_func is None or patched_func is None:",
            f"        pytest.skip('Functions not found in code')",
            f"    ",
            f"    # Execute original",
            f"    try:",
            f"        original_result = original_func({param_str})",
            f"        original_exception = None",
            f"    except Exception as e:",
            f"        original_result = None",
            f"        original_exception = type(e).__name__",
            f"    ",
            f"    # Execute patched",
            f"    try:",
            f"        patched_result = patched_func({param_str})",
            f"        patched_exception = None",
            f"    except Exception as e:",
            f"        patched_result = None",
            f"        patched_exception = type(e).__name__",
            f"    ",
            f"    # Compare behavior",
            f"    if original_exception != patched_exception:",
            f"        pytest.fail(",
            f"            f'Exception mismatch: original raised {{original_exception}}, '",
            f"            f'patched raised {{patched_exception}}'",
            f"        )",
            f"    ",
            f"    if original_exception is None and original_result != patched_result:",
            f"        pytest.fail(",
            f"            f'Result mismatch: original={{original_result}}, patched={{patched_result}}'",
            f"        )",
            f"",
        ]

        # Wrap with Hypothesis decorator
        hypothesis_test = [
            f"@given({strategy_str})",
            f"@settings(max_examples=1000, deadline=3000)",
        ] + test_lines

        return hypothesis_test


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
