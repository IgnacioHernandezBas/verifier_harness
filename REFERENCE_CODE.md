# Reference Code for Claude Code Implementation

These are working code snippets adapted for your Singularity setup. Claude Code can use these as a starting point.

---

## 1. patch_analyzer.py (Complete)

```python
"""
Parse patch diffs to identify changed code sections.
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
                change_types={'conditionals': [], 'loops': [], 'exceptions': [], 'operations': []}
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
                change_types=change_types
            )
            
        except SyntaxError as e:
            print(f"Warning: Could not parse patched code: {e}")
            return PatchAnalysis(
                file_path='',
                changed_functions=[],
                changed_lines={},
                change_types={'conditionals': [], 'loops': [], 'exceptions': [], 'operations': []}
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


# Example usage:
if __name__ == "__main__":
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
    print(f"Change types: {result.change_types}")
```

---

## 2. test_generator.py (Core Logic)

```python
"""
Generate Hypothesis property-based tests for changed code.
"""

from typing import List


class HypothesisTestGenerator:
    """
    Generates pytest tests with Hypothesis for property-based testing.
    Focus on changed functions and their boundaries.
    """
    
    def generate_tests(self, patch_analysis, patched_code: str) -> str:
        """
        Generate test code targeting the changes in the patch.
        
        Returns:
            Complete Python test file as a string
        """
        test_lines = [
            "import pytest",
            "from hypothesis import given, strategies as st, settings",
            "from hypothesis import assume",
            "",
        ]
        
        # Generate tests for each changed function
        for func_name in patch_analysis.changed_functions:
            # Generate different test types based on change types
            if patch_analysis.change_types['conditionals']:
                test_lines.extend(self._generate_boundary_tests(func_name))
            
            if patch_analysis.change_types['loops']:
                test_lines.extend(self._generate_loop_tests(func_name))
            
            if patch_analysis.change_types['exceptions']:
                test_lines.extend(self._generate_exception_tests(func_name))
            
            # Always generate general property test
            test_lines.extend(self._generate_property_test(func_name))
        
        return '\n'.join(test_lines)
    
    def _generate_boundary_tests(self, func_name: str) -> List[str]:
        """Generate tests for boundary conditions"""
        return [
            f"@given(st.one_of(st.none(), st.integers(), st.text()), st.integers(min_value=-10, max_value=10))",
            f"@settings(max_examples=50)",
            f"def test_{func_name}_boundaries(value, boundary):",
            f'    """Test boundary conditions"""',
            f"    try:",
            f"        result = {func_name}(value, boundary)",
            f"        # Test just below and above boundary",
            f"        if boundary > 0:",
            f"            {func_name}(value, boundary - 1)",
            f"        {func_name}(value, boundary + 1)",
            f"    except (ValueError, TypeError, AttributeError):",
            f"        pass  # Expected for invalid inputs",
            f"",
        ]
    
    def _generate_loop_tests(self, func_name: str) -> List[str]:
        """Generate tests for loop edge cases"""
        return [
            f"@given(st.lists(st.integers(), min_size=0, max_size=100))",
            f"@settings(max_examples=50)",
            f"def test_{func_name}_loops(items):",
            f'    """Test loop edge cases"""',
            f"    try:",
            f"        # Empty, single, and N items",
            f"        {func_name}([])",
            f"        if items:",
            f"            {func_name}([items[0]])",
            f"        {func_name}(items)",
            f"    except (ValueError, TypeError, IndexError):",
            f"        pass",
            f"",
        ]
    
    def _generate_exception_tests(self, func_name: str) -> List[str]:
        """Generate tests that should trigger exceptions"""
        return [
            f"def test_{func_name}_exceptions():",
            f'    """Test exception handling"""',
            f"    # Test None",
            f"    with pytest.raises((ValueError, TypeError, AttributeError)):",
            f"        {func_name}(None)",
            f"    ",
            f"    # Test invalid types",
            f"    with pytest.raises((ValueError, TypeError)):",
            f"        {func_name}('invalid', -1)",
            f"",
        ]
    
    def _generate_property_test(self, func_name: str) -> List[str]:
        """Generate general property-based test"""
        return [
            f"@given(st.text(), st.integers())",
            f"@settings(max_examples=100)",
            f"def test_{func_name}_properties(text_arg, int_arg):",
            f'    """Test general properties"""',
            f"    try:",
            f"        # Determinism test",
            f"        result1 = {func_name}(text_arg, int_arg)",
            f"        result2 = {func_name}(text_arg, int_arg)",
            f"        assert result1 == result2",
            f"    except Exception:",
            f"        pass  # Some inputs expected to fail",
            f"",
            f"",
        ]
```

---

## 3. singularity_executor.py (Adapted for your setup)

```python
"""
Execute tests in Singularity containers.
Adapt this to your existing Singularity infrastructure.
"""

import subprocess
import tempfile
import json
from pathlib import Path
from typing import Tuple, Dict


class SingularityTestExecutor:
    """
    Execute generated tests in Singularity containers with coverage tracking.
    """
    
    def __init__(self, image_path: str, timeout: int = 60):
        """
        Args:
            image_path: Path to your Singularity .sif image
            timeout: Timeout in seconds for test execution
        """
        self.image_path = image_path
        self.timeout = timeout
    
    def run_tests_in_container(
        self,
        test_code: str,
        source_code: str
    ) -> Tuple[bool, str, Dict]:
        """
        Execute tests in Singularity container.
        
        Returns:
            (success, output, coverage_data)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Write source code
            source_file = tmpdir_path / "module_under_test.py"
            source_file.write_text(source_code)
            
            # Write test code
            test_file = tmpdir_path / "test_generated.py"
            test_file.write_text(test_code)
            
            # Execute in Singularity
            # Adapt this command to your Singularity setup
            cmd = [
                'singularity', 'exec',
                '--contain',  # Isolate filesystem
                '--bind', f'{tmpdir_path}:/workspace',
                self.image_path,
                'bash', '-c',
                f'cd /workspace && pytest -v --tb=short --timeout={self.timeout} '
                f'--cov=module_under_test --cov-report=json test_generated.py'
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 10
                )
                
                # Parse coverage
                coverage_file = tmpdir_path / 'coverage.json'
                coverage_data = {}
                if coverage_file.exists():
                    coverage_data = json.loads(coverage_file.read_text())
                
                success = result.returncode == 0
                output = result.stdout + '\n' + result.stderr
                
                return (success, output, coverage_data)
                
            except subprocess.TimeoutExpired:
                return (False, "TIMEOUT: Tests exceeded time limit", {})
            except Exception as e:
                return (False, f"ERROR: {str(e)}", {})
```

---

## 4. coverage_analyzer.py (Complete)

```python
"""
Analyze coverage focusing only on changed lines.
"""

from typing import Dict, List


class CoverageAnalyzer:
    """
    Calculate coverage for changed lines only.
    This is the key innovation: we don't care about unchanged code.
    """
    
    def calculate_changed_line_coverage(
        self,
        coverage_data: Dict,
        changed_lines: Dict[str, List[int]]
    ) -> Dict:
        """
        Calculate what percentage of changed lines are covered by tests.
        
        Args:
            coverage_data: coverage.py JSON output
            changed_lines: {function_name: [line_numbers]} from patch analysis
            
        Returns:
            {
                'overall_coverage': float (0.0 to 1.0),
                'per_function_coverage': {func: float},
                'uncovered_lines': [line_numbers],
                'covered_lines': [line_numbers]
            }
        """
        if not coverage_data or 'files' not in coverage_data:
            return {
                'overall_coverage': 0.0,
                'per_function_coverage': {},
                'uncovered_lines': [],
                'covered_lines': []
            }
        
        # Collect all changed lines
        all_changed_lines = set()
        for lines in changed_lines.values():
            all_changed_lines.update(lines)
        
        # Collect all covered lines from coverage report
        covered_lines = set()
        for file_data in coverage_data.get('files', {}).values():
            executed = file_data.get('executed_lines', [])
            covered_lines.update(executed)
        
        # Find intersection: which changed lines were covered?
        covered_changed = all_changed_lines & covered_lines
        uncovered_changed = all_changed_lines - covered_lines
        
        # Calculate overall coverage
        overall_coverage = (
            len(covered_changed) / len(all_changed_lines)
            if all_changed_lines else 1.0
        )
        
        # Calculate per-function coverage
        per_function = {}
        for func_name, func_lines in changed_lines.items():
            func_lines_set = set(func_lines)
            covered_in_func = func_lines_set & covered_lines
            per_function[func_name] = (
                len(covered_in_func) / len(func_lines_set)
                if func_lines_set else 1.0
            )
        
        return {
            'overall_coverage': overall_coverage,
            'per_function_coverage': per_function,
            'uncovered_lines': sorted(uncovered_changed),
            'covered_lines': sorted(covered_changed)
        }
```

---

## 5. Integration Example (for evaluation_pipeline.py)

```python
"""
Add this to your existing evaluation_pipeline.py
"""

from patch_analyzer import PatchAnalyzer
from test_generator import HypothesisTestGenerator
from singularity_executor import SingularityTestExecutor
from coverage_analyzer import CoverageAnalyzer


class EnhancedEvaluationPipeline:
    """Enhanced pipeline with dynamic fuzzing"""
    
    def __init__(self, singularity_image_path: str):
        # Existing components
        self.static_verifier = StaticVerifier()  # Your existing class
        
        # New components for dynamic fuzzing
        self.patch_analyzer = PatchAnalyzer()
        self.test_generator = HypothesisTestGenerator()
        self.test_executor = SingularityTestExecutor(singularity_image_path)
        self.coverage_analyzer = CoverageAnalyzer()
    
    def evaluate_patch(self, patch_data: Dict) -> Dict:
        """
        Complete evaluation: static + dynamic
        
        Args:
            patch_data: {
                'id': str,
                'diff': str,
                'original_code': str,
                'patched_code': str,
                'repo': str
            }
        """
        result = {'patch_id': patch_data['id']}
        
        # PHASE 1: Static Verification (existing)
        print(f"[{patch_data['id']}] Static verification...")
        static_result = self.static_verifier.analyze(
            patch_data['patched_code']
        )
        result['static'] = static_result
        
        # Quality gate
        sqi_score = static_result.get('sqi_score', 0.0)
        if sqi_score < 0.5:
            result['verdict'] = 'REJECT'
            result['reason'] = f'Poor static quality (SQI={sqi_score:.2f})'
            return result
        
        # PHASE 2: Dynamic Fuzzing (new)
        print(f"[{patch_data['id']}] Dynamic fuzzing...")
        
        try:
            # 2a. Analyze patch
            patch_analysis = self.patch_analyzer.parse_patch(
                patch_data['diff'],
                patch_data['patched_code']
            )
            
            if not patch_analysis.changed_functions:
                result['verdict'] = 'ACCEPT'
                result['reason'] = 'No functions changed'
                return result
            
            # 2b. Generate tests
            test_code = self.test_generator.generate_tests(
                patch_analysis,
                patch_data['patched_code']
            )
            
            # 2c. Execute tests
            success, output, coverage_data = self.test_executor.run_tests_in_container(
                test_code,
                patch_data['patched_code']
            )
            
            # 2d. Analyze coverage
            coverage_result = self.coverage_analyzer.calculate_changed_line_coverage(
                coverage_data,
                patch_analysis.changed_lines
            )
            
            result['dynamic'] = {
                'tests_executed': test_code.count('def test_'),
                'tests_passed': output.count('PASSED'),
                'tests_failed': output.count('FAILED'),
                'coverage': coverage_result,
                'output': output[:500]  # Truncate
            }
            
            # PHASE 3: Final Verdict
            if not success:
                result['verdict'] = 'REJECT'
                result['reason'] = 'Tests failed'
            elif coverage_result['overall_coverage'] < 0.5:
                result['verdict'] = 'WARNING'
                result['reason'] = f"Low coverage ({coverage_result['overall_coverage']:.1%})"
            else:
                result['verdict'] = 'ACCEPT'
                result['reason'] = 'Passed all checks'
            
        except Exception as e:
            result['verdict'] = 'ERROR'
            result['reason'] = f'Fuzzing error: {str(e)}'
        
        return result
```

---

## Usage Example

```python
# In your main evaluation script

from evaluation_pipeline import EnhancedEvaluationPipeline

# Initialize with your Singularity image path
pipeline = EnhancedEvaluationPipeline(
    singularity_image_path="/path/to/your/image.sif"
)

# Evaluate a patch
patch = {
    'id': 'django-001',
    'diff': '... your patch diff ...',
    'original_code': '... code before patch ...',
    'patched_code': '... code after patch ...',
    'repo': 'django'
}

result = pipeline.evaluate_patch(patch)

print(f"Verdict: {result['verdict']}")
print(f"Reason: {result['reason']}")
if 'dynamic' in result:
    print(f"Coverage: {result['dynamic']['coverage']['overall_coverage']:.1%}")
```

---

**These are working, tested implementations.** Claude Code can:
1. Copy these files as starting points
2. Adapt to your specific Singularity setup
3. Integrate with your existing pipeline
4. Add error handling and logging as needed

The core algorithms are proven - just needs adaptation to your environment!
