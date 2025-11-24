"""
Learn test patterns from existing test suites.

This module extracts instance creation patterns from existing test files
to generate smarter, more realistic fuzzing tests.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class InstancePattern:
    """Represents a pattern for creating an instance of a class"""
    class_name: str
    parameters: Dict[str, Any]  # {param_name: value}
    source_location: str  # Where this pattern was found
    frequency: int = 1  # How many times this pattern appears


@dataclass
class ClassTestPatterns:
    """Collection of test patterns for a specific class"""
    class_name: str
    patterns: List[InstancePattern] = field(default_factory=list)
    parameter_types: Dict[str, Set[type]] = field(default_factory=lambda: defaultdict(set))
    common_parameters: Dict[str, List[Any]] = field(default_factory=lambda: defaultdict(list))

    def add_pattern(self, pattern: InstancePattern):
        """Add a pattern and update statistics"""
        # Check if similar pattern already exists
        for existing in self.patterns:
            if existing.parameters == pattern.parameters:
                existing.frequency += 1
                return

        self.patterns.append(pattern)

        # Update parameter type and value tracking
        for param_name, value in pattern.parameters.items():
            if value is not None:
                self.parameter_types[param_name].add(type(value))
                self.common_parameters[param_name].append(value)

    def get_most_common_patterns(self, limit: int = 5) -> List[InstancePattern]:
        """Get the most frequently used patterns"""
        sorted_patterns = sorted(self.patterns, key=lambda p: p.frequency, reverse=True)
        return sorted_patterns[:limit]

    def get_parameter_values(self, param_name: str) -> List[Any]:
        """Get all values used for a specific parameter"""
        return self.common_parameters.get(param_name, [])


class TestPatternLearner:
    """
    Extracts instance creation patterns from existing test files.

    Uses AST parsing to find:
    - Constructor calls (ClassName(...))
    - Parameter values used in tests
    - Common parameter combinations
    """

    def __init__(self, repo_path: Path):
        """
        Initialize the pattern learner.

        Args:
            repo_path: Path to the repository containing test files
        """
        self.repo_path = Path(repo_path)
        self.patterns_cache: Dict[str, ClassTestPatterns] = {}

    def learn_patterns(self, class_name: str, module_path: str = None) -> ClassTestPatterns:
        """
        Learn instance creation patterns for a specific class.

        Args:
            class_name: Name of the class to learn patterns for
            module_path: Optional module path to narrow search (e.g., "sklearn.linear_model")

        Returns:
            ClassTestPatterns with learned patterns
        """
        # Check cache
        cache_key = f"{class_name}:{module_path}"
        if cache_key in self.patterns_cache:
            return self.patterns_cache[cache_key]

        patterns = ClassTestPatterns(class_name=class_name)

        # Find test files
        test_files = self._find_test_files(class_name, module_path)

        # Parse each test file
        for test_file in test_files:
            try:
                file_patterns = self._extract_patterns_from_file(test_file, class_name)
                for pattern in file_patterns:
                    patterns.add_pattern(pattern)
            except Exception as e:
                # Continue even if one file fails
                print(f"Warning: Could not parse {test_file}: {e}")
                continue

        # Cache the results
        self.patterns_cache[cache_key] = patterns
        return patterns

    def _find_test_files(self, class_name: str, module_path: str = None) -> List[Path]:
        """
        Find test files that likely test the given class.

        Strategy:
        1. Look for test_*.py files
        2. Search for files containing the class name
        3. If module_path given, prioritize files in that module's test directory
        """
        test_files = []

        # Find all test files
        all_test_files = list(self.repo_path.glob("**/test_*.py"))

        # If we have a module path, prioritize test files in that area
        if module_path:
            # Convert module path to directory path
            # e.g., "sklearn.linear_model" -> "sklearn/linear_model/tests"
            module_parts = module_path.split('.')

            # Try common test directory patterns
            test_dir_patterns = [
                self.repo_path / Path(*module_parts) / "tests",
                self.repo_path / Path(*module_parts) / "test",
                self.repo_path / "tests" / Path(*module_parts),
            ]

            for test_dir in test_dir_patterns:
                if test_dir.exists():
                    test_files.extend(list(test_dir.glob("test_*.py")))

        # Also search all test files for the class name
        for test_file in all_test_files:
            try:
                content = test_file.read_text(encoding='utf-8', errors='ignore')
                if class_name in content:
                    if test_file not in test_files:
                        test_files.append(test_file)
            except Exception:
                continue

        return test_files[:50]  # Limit to first 50 files to avoid too much parsing

    def _extract_patterns_from_file(self, file_path: Path, class_name: str) -> List[InstancePattern]:
        """
        Extract instance creation patterns from a single test file.

        Looks for patterns like:
        - instance = ClassName(param1=value1, param2=value2)
        - ClassName(arg1, arg2, kwarg1=value1)
        """
        patterns = []

        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception as e:
            return patterns

        # Visitor to extract Call nodes
        class CallVisitor(ast.NodeVisitor):
            def __init__(self):
                self.found_patterns = []

            def visit_Call(self, node):
                # Check if this is a call to our target class
                if isinstance(node.func, ast.Name) and node.func.id == class_name:
                    params = self._extract_call_parameters(node)
                    if params is not None:
                        pattern = InstancePattern(
                            class_name=class_name,
                            parameters=params,
                            source_location=f"{file_path.name}:line_{node.lineno}"
                        )
                        self.found_patterns.append(pattern)

                # Also check for ClassName in attribute access (e.g., module.ClassName())
                elif isinstance(node.func, ast.Attribute) and node.func.attr == class_name:
                    params = self._extract_call_parameters(node)
                    if params is not None:
                        pattern = InstancePattern(
                            class_name=class_name,
                            parameters=params,
                            source_location=f"{file_path.name}:line_{node.lineno}"
                        )
                        self.found_patterns.append(pattern)

                self.generic_visit(node)

            def _extract_call_parameters(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
                """Extract parameters from a Call node"""
                params = {}

                try:
                    # Extract keyword arguments
                    for keyword in call_node.keywords:
                        if keyword.arg:  # Skip **kwargs
                            value = self._ast_to_python_value(keyword.value)
                            if value is not None:
                                params[keyword.arg] = value

                    # For positional arguments, we'd need to know the function signature
                    # For now, we focus on keyword arguments which are more explicit

                    return params if params else None
                except Exception:
                    return None

            def _ast_to_python_value(self, node):
                """Convert an AST node to a Python value (best effort)"""
                if isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.Num):  # Python < 3.8
                    return node.n
                elif isinstance(node, ast.Str):  # Python < 3.8
                    return node.s
                elif isinstance(node, ast.NameConstant):  # Python < 3.8
                    return node.value
                elif isinstance(node, ast.List):
                    return [self._ast_to_python_value(elt) for elt in node.elts]
                elif isinstance(node, ast.Tuple):
                    return tuple(self._ast_to_python_value(elt) for elt in node.elts)
                elif isinstance(node, ast.Dict):
                    keys = [self._ast_to_python_value(k) for k in node.keys]
                    values = [self._ast_to_python_value(v) for v in node.values]
                    return dict(zip(keys, values))
                elif isinstance(node, ast.Name):
                    # For simple names like None, True, False
                    if node.id in ('None', 'True', 'False'):
                        return eval(node.id)
                    # For other names, return a placeholder
                    return f"<{node.id}>"
                elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                    # Negative numbers
                    val = self._ast_to_python_value(node.operand)
                    return -val if isinstance(val, (int, float)) else None
                else:
                    # For complex expressions, return a string representation
                    return f"<complex:{type(node).__name__}>"

        visitor = CallVisitor()
        visitor.visit(tree)
        patterns.extend(visitor.found_patterns)

        return patterns

    def generate_hypothesis_strategy_from_patterns(self, patterns: ClassTestPatterns) -> str:
        """
        Generate Hypothesis strategy code based on learned patterns.

        Returns:
            Python code string for Hypothesis strategies
        """
        if not patterns.patterns:
            return None

        strategies = []

        # For each parameter, generate a strategy based on observed values
        for param_name, values in patterns.common_parameters.items():
            if not values:
                continue

            # Filter out complex values that can't be easily used
            simple_values = [v for v in values if not isinstance(v, str) or not v.startswith('<')]

            if not simple_values:
                continue

            # Get unique values
            unique_values = list(set(str(v) for v in simple_values))[:10]  # Limit to 10

            # Generate strategy
            if len(unique_values) <= 5:
                # For small sets, use sampled_from
                strategy = f"st.sampled_from({simple_values[:5]})"
            else:
                # For larger sets, infer type-based strategy
                value_types = set(type(v) for v in simple_values)

                if int in value_types or float in value_types:
                    nums = [v for v in simple_values if isinstance(v, (int, float))]
                    if nums:
                        min_val = min(nums)
                        max_val = max(nums)
                        if int in value_types:
                            strategy = f"st.integers(min_value={min_val}, max_value={max_val})"
                        else:
                            strategy = f"st.floats(min_value={min_val}, max_value={max_val})"
                elif bool in value_types:
                    strategy = "st.booleans()"
                elif str in value_types:
                    strs = [v for v in simple_values if isinstance(v, str)]
                    strategy = f"st.sampled_from({strs[:5]})"
                elif list in value_types:
                    strategy = f"st.sampled_from({simple_values[:3]})"
                else:
                    strategy = f"st.sampled_from({simple_values[:3]})"

            strategies.append((param_name, strategy))

        return strategies


# Example usage
if __name__ == "__main__":
    # Test with a sample repository
    learner = TestPatternLearner(Path("/path/to/repo"))
    patterns = learner.learn_patterns("RidgeClassifierCV", "sklearn.linear_model.ridge")

    print(f"Found {len(patterns.patterns)} patterns")
    print("\nMost common patterns:")
    for pattern in patterns.get_most_common_patterns():
        print(f"  {pattern.parameters} (used {pattern.frequency} times)")

    print("\nParameter values:")
    for param_name, values in patterns.common_parameters.items():
        print(f"  {param_name}: {values[:5]}")
