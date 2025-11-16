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


class PatchAnalyzer:
    """
    Analyzes unified diff patches to extract:
    - Which functions changed
    - Which lines changed
    - What type of changes (conditionals, loops, etc.)
    """

    def parse_patch(self, patch_content: str, patched_code: str) -> PatchAnalysis:
        """
        Parse a unified diff patch.

        Args:
            patch_content: Unified diff string (+++, ---, @@, +, -)
            patched_code: The code after applying the patch

        Returns:
            PatchAnalysis with structured information about changes
        """
        # Extract changed line numbers from diff
        changed_line_numbers = self._extract_changed_lines(patch_content)

        if not changed_line_numbers:
            return PatchAnalysis(
                file_path='',
                changed_functions=[],
                changed_lines={},
                change_types={'conditionals': [], 'loops': [], 'exceptions': [], 'operations': []},
                all_changed_lines=[]
            )

        # Parse the patched code to map lines to functions
        try:
            tree = ast.parse(patched_code)
            changed_functions = []
            changed_lines_by_func = {}
            change_types = {
                'conditionals': [],
                'loops': [],
                'exceptions': [],
                'operations': []
            }

            # Walk the AST to find functions containing changes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    func_start = node.lineno
                    func_end = node.end_lineno if node.end_lineno else func_start

                    # Check if any changed lines fall within this function
                    func_changed_lines = [
                        ln for ln in changed_line_numbers
                        if func_start <= ln <= func_end
                    ]

                    if func_changed_lines:
                        changed_functions.append(func_name)
                        changed_lines_by_func[func_name] = func_changed_lines

                        # Classify the types of changes
                        self._classify_changes(node, func_changed_lines, change_types)

            return PatchAnalysis(
                file_path='',
                changed_functions=changed_functions,
                changed_lines=changed_lines_by_func,
                change_types=change_types,
                all_changed_lines=changed_line_numbers
            )

        except SyntaxError as e:
            print(f"Warning: Could not parse patched code: {e}")
            return PatchAnalysis(
                file_path='',
                changed_functions=[],
                changed_lines={},
                change_types={'conditionals': [], 'loops': [], 'exceptions': [], 'operations': []},
                all_changed_lines=changed_line_numbers
            )

    def _extract_changed_lines(self, patch_content: str) -> List[int]:
        """
        Extract line numbers that were added/modified from unified diff.

        Unified diff format:
        @@ -old_start,old_count +new_start,new_count @@
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
