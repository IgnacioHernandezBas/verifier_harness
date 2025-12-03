"""
Parse patch diffs to identify changed code sections.

This module analyzes unified diff patches to extract:
- Which functions changed
- Which specific lines changed
- What type of changes occurred (conditionals, loops, exceptions, etc.)

This forms the foundation of change-aware fuzzing.
"""

import ast
import re
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class PatchAnalysis:
    """Results from patch analysis"""
    file_path: str
    changed_functions: List[str]
    changed_lines: Dict[str, List[int]]  # {function_name: [line_numbers]}
    change_types: Dict[str, List[Dict]]
    all_changed_lines: List[int]  # All changed lines regardless of function
    module_path: str = ""  # e.g., "_pytest.logging" derived from "src/_pytest/logging.py"
    class_context: Dict[str, str] = None  # {function_name: class_name} for methods


class PatchAnalyzer:
    """
    Analyzes unified diff patches to extract:
    - Which functions changed
    - Which lines changed
    - What type of changes (conditionals, loops, etc.)
    """

    def parse_patch(self, patch_content: str, patched_code: str, file_path: str = "") -> PatchAnalysis:
        """
        Parse a unified diff patch.

        Args:
            patch_content: Unified diff string (+++, ---, @@, +, -)
            patched_code: The code after applying the patch
            file_path: Path to the modified file (e.g., "src/_pytest/logging.py")

        Returns:
            PatchAnalysis with structured information about changes
        """
        # Extract file path from patch if not provided
        if not file_path:
            file_path = self._extract_file_path(patch_content)

        # Convert file path to module path (e.g., "src/_pytest/logging.py" -> "_pytest.logging")
        module_path = self._file_path_to_module(file_path)

        # Extract changed line numbers from diff
        changed_line_numbers = self._extract_changed_lines(patch_content)

        if not changed_line_numbers:
            return PatchAnalysis(
                file_path=file_path,
                changed_functions=[],
                changed_lines={},
                change_types={'conditionals': [], 'loops': [], 'exceptions': [], 'operations': []},
                all_changed_lines=[],
                module_path=module_path,
                class_context={}
            )

        # Extract context from diff headers (fallback if AST matching fails)
        diff_contexts = self._extract_context_from_diff(patch_content)

        # Parse the patched code to map lines to functions and classes
        try:
            tree = ast.parse(patched_code)
            changed_functions = []
            changed_lines_by_func = {}
            class_context = {}  # {function_name: class_name}
            change_types = {
                'conditionals': [],
                'loops': [],
                'exceptions': [],
                'operations': []
            }

            # Walk the AST to find classes and their methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    # Check methods within this class
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            func_name = item.name
                            func_start = item.lineno
                            func_end = item.end_lineno if item.end_lineno else func_start

                            # Check if any changed lines fall within this method
                            func_changed_lines = [
                                ln for ln in changed_line_numbers
                                if func_start <= ln <= func_end
                            ]

                            if func_changed_lines:
                                changed_functions.append(func_name)
                                changed_lines_by_func[func_name] = func_changed_lines
                                class_context[func_name] = class_name

                                # Classify the types of changes
                                self._classify_changes(item, func_changed_lines, change_types)

            # Also check for top-level functions (not in a class)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip if already processed as class method
                    if node.name in class_context:
                        continue

                    func_name = node.name
                    func_start = node.lineno
                    func_end = node.end_lineno if node.end_lineno else func_start

                    func_changed_lines = [
                        ln for ln in changed_line_numbers
                        if func_start <= ln <= func_end
                    ]

                    if func_changed_lines:
                        changed_functions.append(func_name)
                        changed_lines_by_func[func_name] = func_changed_lines
                        # No class context for top-level functions

                        self._classify_changes(node, func_changed_lines, change_types)

            # Fallback: If AST matching found no functions, use diff context
            if not changed_functions and diff_contexts:
                print(f"  ℹ️  AST matching found no functions, using diff context as fallback")
                for ctx in diff_contexts:
                    func_name = ctx.get('func_name')
                    class_name = ctx.get('class_name')

                    # Use function name if available, otherwise use class name
                    if func_name:
                        changed_functions.append(func_name)
                        changed_lines_by_func[func_name] = changed_line_numbers
                        if class_name:
                            class_context[func_name] = class_name
                    elif class_name and class_name not in changed_functions:
                        # Class-level changes (like docstrings)
                        changed_functions.append(class_name)
                        changed_lines_by_func[class_name] = changed_line_numbers

            return PatchAnalysis(
                file_path=file_path,
                changed_functions=changed_functions,
                changed_lines=changed_lines_by_func,
                change_types=change_types,
                all_changed_lines=changed_line_numbers,
                module_path=module_path,
                class_context=class_context
            )

        except SyntaxError as e:
            print(f"Warning: Could not parse patched code: {e}")
            return PatchAnalysis(
                file_path=file_path,
                changed_functions=[],
                changed_lines={},
                change_types={'conditionals': [], 'loops': [], 'exceptions': [], 'operations': []},
                all_changed_lines=changed_line_numbers,
                module_path=module_path,
                class_context={}
            )

    def _extract_changed_lines(self, patch_content: str) -> List[int]:
        """
        Extract line numbers that were added/modified from unified diff.

        Unified diff format:
        @@ -old_start,old_count +new_start,new_count @@ context
        """
        changed_lines = []
        lines = patch_content.split('\n')
        current_line = 0

        for line in lines:
            # Parse hunk header to get starting line number
            if line.startswith('@@'):
                match = re.search(r'\+(\d+)', line)
                if match:
                    current_line = int(match.group(1))
            # Lines starting with + (but not +++) are additions/changes
            elif line.startswith('+') and not line.startswith('+++'):
                changed_lines.append(current_line)
                current_line += 1
            # Lines not starting with - increment the line counter
            elif not line.startswith('-'):
                current_line += 1

        return changed_lines

    def _extract_context_from_diff(self, patch_content: str) -> List[Dict[str, str]]:
        """
        Extract function/class context from @@ headers.

        Returns list of {class_name, func_name, line_start}
        """
        contexts = []
        lines = patch_content.split('\n')

        for line in lines:
            if line.startswith('@@'):
                # Extract context after second @@
                # Format: @@ -old +new @@ context
                parts = line.split('@@')
                if len(parts) >= 3:
                    context = parts[2].strip()

                    # Extract line number
                    match = re.search(r'\+(\d+)', line)
                    line_start = int(match.group(1)) if match else 0

                    # Parse context for class and function
                    class_name = None
                    func_name = None

                    # Look for "class ClassName" or "def function_name"
                    class_match = re.search(r'class\s+(\w+)', context)
                    func_match = re.search(r'def\s+(\w+)', context)

                    if class_match:
                        class_name = class_match.group(1)
                    if func_match:
                        func_name = func_match.group(1)

                    if class_name or func_name:
                        contexts.append({
                            'class_name': class_name,
                            'func_name': func_name,
                            'line_start': line_start
                        })

        return contexts

    def _classify_changes(self, func_node, changed_lines: List[int], change_types: Dict):
        """Classify what types of code constructs changed"""
        for node in ast.walk(func_node):
            if hasattr(node, 'lineno') and node.lineno in changed_lines:
                if isinstance(node, (ast.If, ast.IfExp)):
                    change_types['conditionals'].append({
                        'line': node.lineno,
                        'type': 'if_statement'
                    })
                elif isinstance(node, (ast.For, ast.While)):
                    change_types['loops'].append({
                        'line': node.lineno,
                        'type': 'loop'
                    })
                elif isinstance(node, (ast.Raise, ast.Try, ast.ExceptHandler)):
                    change_types['exceptions'].append({
                        'line': node.lineno,
                        'type': 'exception'
                    })
                elif isinstance(node, (ast.Compare, ast.BinOp, ast.BoolOp)):
                    change_types['operations'].append({
                        'line': node.lineno,
                        'type': 'operation'
                    })

    def _extract_file_path(self, patch_content: str) -> str:
        """Extract file path from unified diff header"""
        for line in patch_content.split('\n'):
            if line.startswith('+++'):
                # Extract path after '+++ b/'
                path = line.split(' ', 1)[1] if ' ' in line else ''
                if path.startswith('b/'):
                    path = path[2:]  # Remove 'b/' prefix
                return path
        return ''

    def _file_path_to_module(self, file_path: str) -> str:
        """
        Convert file path to Python module path.
        Examples:
            "src/_pytest/logging.py" -> "_pytest.logging"
            "lib/mymodule/utils.py" -> "mymodule.utils"
            "myfile.py" -> "myfile"
        """
        if not file_path or not file_path.endswith('.py'):
            return ''

        # Remove .py extension
        path_without_ext = file_path[:-3]

        # Remove common source directory prefixes
        for prefix in ['src/', 'lib/', 'source/']:
            if path_without_ext.startswith(prefix):
                path_without_ext = path_without_ext[len(prefix):]
                break

        # Convert path separators to dots
        module_path = path_without_ext.replace('/', '.')

        return module_path


# Example usage and testing
if __name__ == "__main__":
    # Test with a simple patch
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
    result = analyzer.parse_patch(patch_diff, patched_code)

    print(f"Changed functions: {result.changed_functions}")
    print(f"Changed lines: {result.changed_lines}")
    print(f"All changed lines: {result.all_changed_lines}")
    print(f"Change types: {result.change_types}")
