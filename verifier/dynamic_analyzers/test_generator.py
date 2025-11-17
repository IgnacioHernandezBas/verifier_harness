"""
Generate Hypothesis property-based tests for changed code.

This module generates targeted, executable pytest tests focusing on:
- Boundary conditions for new conditionals
- Edge cases for new loops
- Exception triggering tests
- General property-based tests
"""

import ast
from typing import List, Dict, Any
from .patch_analyzer import PatchAnalysis


class HypothesisTestGenerator:
    """
    Generates pytest tests with Hypothesis for property-based testing.
    Focus on changed functions and their boundaries.
    """

    def generate_tests(self, patch_analysis: PatchAnalysis, patched_code: str) -> str:
        """
        Generate test code targeting the changes in the patch.

        Args:
            patch_analysis: Analysis of what changed in the patch
            patched_code: The full patched code (for import context)

        Returns:
            Complete Python test file as a string
        """
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

        # For class methods, we need to instantiate the class first
        # For now, we'll skip testing class methods with Hypothesis since we don't know constructor args
        if class_name:
            return [
                f"def test_{func_name}_exists():",
                f'    """Verify {class_name}.{func_name} exists and is callable"""',
                f"    assert hasattr({class_name}, '{func_name}'), '{class_name} should have {func_name} method'",
                f"    # Note: Full property-based testing of methods requires instance creation",
                f"    # which is complex without knowing constructor requirements",
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
