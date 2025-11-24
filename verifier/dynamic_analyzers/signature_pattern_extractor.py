"""
Extract test patterns from function signatures when no existing tests are available.

This is a fallback for LLM-generated code or new functions where pattern learning
from existing tests is not possible.

Strategies:
1. Use type hints to infer parameter strategies
2. Use default values as test patterns
3. Infer types from parameter names (heuristics)
"""

import ast
import inspect
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SignaturePattern:
    """Pattern extracted from a function signature"""
    param_name: str
    param_type: Optional[type]
    default_value: Any
    has_default: bool
    annotation: Optional[str]


class SignaturePatternExtractor:
    """
    Extract test patterns from function signatures.

    Used as a fallback when no existing tests are available to learn from.
    """

    def extract_from_code(self, code: str, class_name: str = None,
                         func_name: str = "__init__") -> List[SignaturePattern]:
        """
        Extract signature patterns from Python code.

        Args:
            code: Python source code
            class_name: Name of class (if method)
            func_name: Name of function/method

        Returns:
            List of SignaturePattern objects
        """
        try:
            tree = ast.parse(code)

            # Find the target function
            for node in ast.walk(tree):
                # Check for class methods
                if class_name and isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == func_name:
                            return self._extract_from_function_def(item)

                # Check for standalone functions
                if not class_name and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    return self._extract_from_function_def(node)

            return []

        except Exception as e:
            print(f"Warning: Could not extract signature patterns: {e}")
            return []

    def _extract_from_function_def(self, func_node: ast.FunctionDef) -> List[SignaturePattern]:
        """Extract patterns from a function definition AST node"""
        patterns = []

        args = func_node.args

        # Get defaults (aligned with the end of args list)
        defaults = args.defaults or []
        num_args = len(args.args)
        num_defaults = len(defaults)

        for i, arg in enumerate(args.args):
            # Skip self and cls
            if arg.arg in ('self', 'cls'):
                continue

            # Get default value if available
            default_index = i - (num_args - num_defaults)
            has_default = default_index >= 0
            default_value = None

            if has_default:
                default_node = defaults[default_index]
                default_value = self._ast_to_python_value(default_node)

            # Get type annotation if available
            annotation = None
            annotation_str = None
            if arg.annotation:
                annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else None
                annotation = self._parse_type_annotation(arg.annotation)

            pattern = SignaturePattern(
                param_name=arg.arg,
                param_type=annotation,
                default_value=default_value,
                has_default=has_default,
                annotation=annotation_str
            )

            patterns.append(pattern)

        return patterns

    def _ast_to_python_value(self, node):
        """Convert AST node to Python value"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.NameConstant):
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
            if node.id in ('None', 'True', 'False'):
                return eval(node.id)
            return f"<{node.id}>"
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            val = self._ast_to_python_value(node.operand)
            return -val if isinstance(val, (int, float)) else None
        else:
            return None

    def _parse_type_annotation(self, annotation_node) -> Optional[type]:
        """Parse type annotation to Python type"""
        if isinstance(annotation_node, ast.Name):
            type_map = {
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
            }
            return type_map.get(annotation_node.id)

        # For complex types like List[int], Optional[str], etc.
        # We'll just return None for now
        return None

    def generate_hypothesis_strategies(self, patterns: List[SignaturePattern]) -> List[Tuple[str, str]]:
        """
        Generate Hypothesis strategies from signature patterns.

        Args:
            patterns: List of SignaturePattern objects

        Returns:
            List of (param_name, strategy_code) tuples
        """
        strategies = []

        for pattern in patterns:
            strategy = self._generate_strategy_for_pattern(pattern)
            if strategy:
                strategies.append((pattern.param_name, strategy))

        return strategies

    def _generate_strategy_for_pattern(self, pattern: SignaturePattern) -> Optional[str]:
        """Generate a Hypothesis strategy for a single parameter"""

        # Strategy 1: Use default value if available
        if pattern.has_default and pattern.default_value is not None:
            # If default is a simple value, create strategy around it
            if isinstance(pattern.default_value, bool):
                return "st.booleans()"
            elif isinstance(pattern.default_value, int):
                # Generate integers around the default value
                val = pattern.default_value
                return f"st.integers(min_value={max(0, val-10)}, max_value={val+10})"
            elif isinstance(pattern.default_value, float):
                val = pattern.default_value
                return f"st.floats(min_value={max(0.0, val-1.0)}, max_value={val+1.0})"
            elif isinstance(pattern.default_value, str):
                return f"st.sampled_from([{repr(pattern.default_value)}, ''])"
            elif isinstance(pattern.default_value, (list, tuple)):
                # Use the default value itself
                return f"st.just({repr(pattern.default_value)})"
            elif pattern.default_value is None:
                # None default - could be optional
                return "st.none()"

        # Strategy 2: Use type annotation
        if pattern.param_type:
            if pattern.param_type == int:
                return "st.integers(min_value=0, max_value=100)"
            elif pattern.param_type == float:
                return "st.floats(min_value=0.0, max_value=1.0)"
            elif pattern.param_type == str:
                return "st.text(min_size=1, max_size=10)"
            elif pattern.param_type == bool:
                return "st.booleans()"
            elif pattern.param_type == list:
                return "st.lists(st.integers(), min_size=0, max_size=5)"
            elif pattern.param_type == dict:
                return "st.dictionaries(st.text(), st.integers())"

        # Strategy 3: Heuristics based on parameter name
        name_lower = pattern.param_name.lower()

        if 'threshold' in name_lower or 'alpha' in name_lower or 'beta' in name_lower:
            return "st.floats(min_value=0.0, max_value=1.0)"
        elif 'rate' in name_lower:
            return "st.floats(min_value=0.0, max_value=1.0)"
        elif 'size' in name_lower or 'count' in name_lower or 'num' in name_lower or 'n_' in name_lower:
            return "st.integers(min_value=1, max_value=100)"
        elif 'flag' in name_lower or 'enable' in name_lower or 'is_' in name_lower or name_lower.startswith('use_'):
            return "st.booleans()"
        elif 'name' in name_lower or 'label' in name_lower:
            return "st.text(min_size=1, max_size=20)"
        elif 'data' in name_lower or 'array' in name_lower or 'values' in name_lower:
            return "st.lists(st.floats(), min_size=1, max_size=10)"

        # Default: try a mixed strategy
        return "st.one_of(st.none(), st.integers(), st.floats(), st.text())"

    def generate_default_based_test(self, class_name: str, func_name: str,
                                    patterns: List[SignaturePattern]) -> Dict[str, Any]:
        """
        Generate a test using default values from signature.

        Returns:
            Dictionary with parameter values for testing
        """
        test_params = {}

        for pattern in patterns:
            if pattern.has_default:
                test_params[pattern.param_name] = pattern.default_value
            elif pattern.param_type == bool:
                test_params[pattern.param_name] = False
            elif pattern.param_type == int:
                test_params[pattern.param_name] = 0
            elif pattern.param_type == float:
                test_params[pattern.param_name] = 0.0
            elif pattern.param_type == str:
                test_params[pattern.param_name] = ""
            # For others, don't include (will use kwargs in test)

        return test_params


# Example usage
if __name__ == "__main__":
    code = """
class NewEstimator:
    def __init__(self, alpha: float = 0.5, n_iterations: int = 100,
                 normalize: bool = True, penalty=None):
        self.alpha = alpha
        self.n_iterations = n_iterations
        self.normalize = normalize
        self.penalty = penalty
"""

    extractor = SignaturePatternExtractor()
    patterns = extractor.extract_from_code(code, "NewEstimator", "__init__")

    print("Extracted Signature Patterns:")
    for p in patterns:
        print(f"  {p.param_name}: type={p.annotation}, default={p.default_value}, has_default={p.has_default}")

    print("\nGenerated Hypothesis Strategies:")
    strategies = extractor.generate_hypothesis_strategies(patterns)
    for name, strategy in strategies:
        print(f"  {name} = {strategy}")

    print("\nDefault-based Test Parameters:")
    test_params = extractor.generate_default_based_test("NewEstimator", "__init__", patterns)
    print(f"  {test_params}")
