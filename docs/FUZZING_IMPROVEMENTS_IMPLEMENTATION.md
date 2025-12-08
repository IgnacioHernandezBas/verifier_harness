# Implementation Guide: Improving Fuzzing Effectiveness

## Overview

This guide provides **ready-to-implement code** to fix the 7 critical weaknesses identified in `FUZZING_APPROACH_ANALYSIS.md`. Each improvement includes:
- Code snippets
- Integration instructions
- Test examples
- Expected outcomes

---

## Improvement 1: Differential Testing Framework

### What It Does
Compares behavior between original and patched code to detect divergences.

### Implementation

Create `verifier/dynamic_analyzers/differential_tester.py`:

```python
"""
Differential testing to detect behavioral divergences between original and patched code.
"""

import ast
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from hypothesis import given, strategies as st, settings


@dataclass
class BehavioralDivergence:
    """Record of a behavioral difference between original and patched code."""

    test_input: Dict[str, Any]
    original_result: Any
    patched_result: Any
    original_exception: Optional[str]
    patched_exception: Optional[str]
    divergence_type: str  # "result", "exception", "both"

    def __str__(self):
        if self.divergence_type == "exception":
            return (
                f"Exception divergence: "
                f"Original: {self.original_exception}, "
                f"Patched: {self.patched_exception}"
            )
        elif self.divergence_type == "result":
            return (
                f"Result divergence: "
                f"Original: {self.original_result}, "
                f"Patched: {self.patched_result}"
            )
        else:
            return (
                f"Full divergence: "
                f"Original: {self.original_exception or self.original_result}, "
                f"Patched: {self.patched_exception or self.patched_result}"
            )


class DifferentialFuzzer:
    """
    Compare behavior between original and patched code using property-based testing.
    """

    def __init__(self, original_code: str, patched_code: str, function_name: str):
        """
        Initialize differential fuzzer.

        Args:
            original_code: Python code before patch
            patched_code: Python code after patch
            function_name: Name of function to test
        """
        self.original_code = original_code
        self.patched_code = patched_code
        self.function_name = function_name
        self.divergences: List[BehavioralDivergence] = []

    def _load_function(self, code: str, func_name: str):
        """Load a function from code string."""
        namespace = {}
        exec(code, namespace)
        return namespace.get(func_name)

    def _execute_with_exception_capture(self, func, *args, **kwargs) -> Tuple[Any, Optional[str]]:
        """
        Execute function and capture result or exception.

        Returns:
            (result, exception_type) tuple
            If exception occurs: (None, "ValueError")
            If no exception: (result, None)
        """
        try:
            result = func(*args, **kwargs)
            return result, None
        except Exception as e:
            return None, type(e).__name__

    def compare_behavior(self, *args, **kwargs) -> Optional[BehavioralDivergence]:
        """
        Compare behavior for given inputs.

        Returns:
            BehavioralDivergence if divergence detected, None otherwise
        """
        original_func = self._load_function(self.original_code, self.function_name)
        patched_func = self._load_function(self.patched_code, self.function_name)

        if original_func is None or patched_func is None:
            return None

        # Execute both versions
        orig_result, orig_exc = self._execute_with_exception_capture(original_func, *args, **kwargs)
        patch_result, patch_exc = self._execute_with_exception_capture(patched_func, *args, **kwargs)

        # Check for divergences
        exception_divergence = orig_exc != patch_exc
        result_divergence = (orig_exc is None and patch_exc is None and orig_result != patch_result)

        if exception_divergence or result_divergence:
            divergence_type = "both" if (exception_divergence and result_divergence) else \
                            "exception" if exception_divergence else "result"

            divergence = BehavioralDivergence(
                test_input={"args": args, "kwargs": kwargs},
                original_result=orig_result,
                patched_result=patch_result,
                original_exception=orig_exc,
                patched_exception=patch_exc,
                divergence_type=divergence_type
            )

            self.divergences.append(divergence)
            return divergence

        return None

    def generate_differential_tests(self, strategies: Dict[str, Any], max_examples: int = 500) -> str:
        """
        Generate Hypothesis tests for differential testing.

        Args:
            strategies: Dict of {param_name: strategy_code}
            max_examples: Number of test cases to generate

        Returns:
            Python test code as string
        """
        params = list(strategies.keys())
        strategy_list = [f"{param}={strategies[param]}" for param in params]
        param_str = ", ".join(params)

        test_code = f'''
import pytest
from hypothesis import given, strategies as st, settings

def load_function(code: str, func_name: str):
    namespace = {{}}
    exec(code, namespace)
    return namespace.get(func_name)

original_code = """
{self.original_code}
"""

patched_code = """
{self.patched_code}
"""

@given({", ".join(strategy_list)})
@settings(max_examples={max_examples}, deadline=2000)
def test_{self.function_name}_differential({param_str}):
    """Test behavioral equivalence between original and patched code."""

    original_func = load_function(original_code, "{self.function_name}")
    patched_func = load_function(patched_code, "{self.function_name}")

    # Execute original
    try:
        original_result = original_func({param_str})
        original_exception = None
    except Exception as e:
        original_result = None
        original_exception = type(e).__name__

    # Execute patched
    try:
        patched_result = patched_func({param_str})
        patched_exception = None
    except Exception as e:
        patched_result = None
        patched_exception = type(e).__name__

    # Compare behavior
    if original_exception != patched_exception:
        pytest.fail(
            f"Exception mismatch: original raised {{original_exception}}, "
            f"patched raised {{patched_exception}}"
        )

    if original_exception is None and original_result != patched_result:
        pytest.fail(
            f"Result mismatch: original={{original_result}}, patched={{patched_result}}"
        )
'''
        return test_code
```

### Integration

Update `verifier/dynamic_analyzers/test_generator.py`:

```python
# Add to imports
from .differential_tester import DifferentialFuzzer

class HypothesisTestGenerator:
    def __init__(self, repo_path: Optional[Path] = None, enable_differential: bool = True):
        # Existing code...
        self.enable_differential = enable_differential

    def generate_tests(self, patch_analysis: PatchAnalysis, patched_code: str,
                      original_code: str = None) -> str:
        """
        Generate test code targeting the changes in the patch.

        Args:
            patch_analysis: Analysis of what changed
            patched_code: Code after patch
            original_code: Code before patch (for differential testing)
        """
        test_lines = [
            "# Auto-generated change-aware fuzzing tests",
            "import pytest",
            "from hypothesis import given, strategies as st, settings",
            "",
        ]

        # Existing test generation...

        # Add differential tests if original code available
        if self.enable_differential and original_code:
            test_lines.append("# === DIFFERENTIAL TESTS ===")
            test_lines.append("")

            for func_name in patch_analysis.changed_functions:
                diff_fuzzer = DifferentialFuzzer(
                    original_code=original_code,
                    patched_code=patched_code,
                    function_name=func_name
                )

                # Generate strategies for this function
                strategies = self._generate_strategies_for_function(func_name)

                diff_test = diff_fuzzer.generate_differential_tests(
                    strategies=strategies,
                    max_examples=500
                )

                test_lines.append(diff_test)
                test_lines.append("")

        return '\n'.join(test_lines)
```

### Usage Example

```python
from verifier.dynamic_analyzers.differential_tester import DifferentialFuzzer

original = """
def should_retry(count: int) -> bool:
    return count >= 3
"""

patched = """
def should_retry(count: int) -> bool:
    return count > 3  # Off-by-one error!
"""

fuzzer = DifferentialFuzzer(original, patched, "should_retry")

# Test specific input
divergence = fuzzer.compare_behavior(3)
if divergence:
    print(f"Divergence detected: {divergence}")
    # Output: Result divergence: Original: True, Patched: False

# Generate Hypothesis tests
test_code = fuzzer.generate_differential_tests(
    strategies={"count": "st.integers(min_value=0, max_value=10)"}
)
print(test_code)
```

---

## Improvement 2: Boundary-Aware Strategy Generation

### What It Does
Extracts boundary values from patch conditionals and tests around them.

### Implementation

Add to `verifier/dynamic_analyzers/test_generator.py`:

```python
class HypothesisTestGenerator:
    def _extract_boundaries_from_patch(self, patch_content: str, patched_code: str) -> Dict[str, List[Any]]:
        """
        Extract boundary values from conditionals in the patch.

        Returns:
            Dict of {variable_name: [boundary_values]}
        """
        boundaries = {}

        # Parse patch to find changed conditionals
        import re

        # Pattern: variable [><=] number
        pattern = r'([a-zA-Z_]\w*)\s*([><=]+)\s*(-?\d+(?:\.\d+)?)'

        for line in patch_content.split('\n'):
            if line.startswith('+'):  # Changed line
                matches = re.findall(pattern, line)
                for var, op, value in matches:
                    num_value = float(value) if '.' in value else int(value)

                    if var not in boundaries:
                        boundaries[var] = set()

                    # Add boundary-1, boundary, boundary+1
                    if isinstance(num_value, int):
                        boundaries[var].add(num_value - 1)
                        boundaries[var].add(num_value)
                        boundaries[var].add(num_value + 1)
                    else:
                        boundaries[var].add(num_value - 0.1)
                        boundaries[var].add(num_value)
                        boundaries[var].add(num_value + 0.1)

        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in boundaries.items()}

    def _generate_boundary_aware_strategy(self, param_name: str, boundaries: Dict[str, List]) -> str:
        """
        Generate Hypothesis strategy that includes boundary values.

        Args:
            param_name: Parameter name
            boundaries: Boundary values extracted from patch

        Returns:
            Hypothesis strategy code as string
        """
        if param_name in boundaries:
            # Use sampled_from for boundary values + random values
            boundary_values = boundaries[param_name]
            return (
                f"st.one_of("
                f"st.sampled_from({boundary_values}), "  # Boundary values
                f"st.integers(min_value={min(boundary_values)-10}, max_value={max(boundary_values)+10})"  # Random values
                f")"
            )
        else:
            # Fall back to existing strategy inference
            return self._infer_smart_strategy_for_param(param_name, {})

    def _generate_boundary_tests(self, func_name: str, func_sig: Dict,
                                 class_name: str = None, patch_content: str = "") -> List[str]:
        """Enhanced boundary tests with patch-aware boundaries."""

        # Extract boundaries from patch
        boundaries = self._extract_boundaries_from_patch(patch_content, self.patched_code_cache)

        # Generate strategies
        params = func_sig.get('params', [])
        if not params:
            return []

        strategies = []
        for param in params[:5]:  # Limit to 5 params
            strategy = self._generate_boundary_aware_strategy(param, boundaries)
            strategies.append(f"{param}={strategy}")

        param_str = ", ".join(params[:5])

        return [
            f"@given({', '.join(strategies)})",
            f"@settings(max_examples=500, deadline=2000)",  # Increased from 50
            f"def test_{func_name}_boundary_aware({param_str}):",
            f'    """Test boundary conditions from patch analysis"""',
            f"    # Boundaries detected: {boundaries}",
            f"    try:",
            f"        result = {func_name}({param_str})",
            f"        # Verify determinism",
            f"        result2 = {func_name}({param_str})",
            f"        assert result == result2, 'Should be deterministic'",
            f"    except Exception as e:",
            f"        # Record exception for analysis",
            f"        pass  # TODO: Compare with original behavior",
            f"",
        ]
```

### Usage Example

```python
patch = """
@@ -10,7 +10,7 @@ def should_retry(count: int) -> bool:
-    return count >= 3
+    return count > 3
"""

generator = HypothesisTestGenerator()
boundaries = generator._extract_boundaries_from_patch(patch, patched_code)
# Returns: {'count': [2, 3, 4]}

strategy = generator._generate_boundary_aware_strategy('count', boundaries)
# Returns: "st.one_of(st.sampled_from([2, 3, 4]), st.integers(min_value=-8, max_value=14))"
```

---

## Improvement 3: Exception Recording and Analysis

### What It Does
Records all exceptions instead of ignoring them, enabling pattern analysis.

### Implementation

Create `verifier/dynamic_analyzers/exception_tracker.py`:

```python
"""
Track and analyze exception patterns in fuzzing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from collections import Counter


@dataclass
class ExceptionRecord:
    """Record of an exception occurrence."""
    exception_type: str
    test_input: Dict
    message: str
    frequency: int = 1


class ExceptionTracker:
    """Track exceptions during fuzzing to detect behavioral changes."""

    def __init__(self):
        self.exceptions: List[ExceptionRecord] = []
        self.exception_counts: Counter = Counter()

    def record_exception(self, exception_type: str, test_input: Dict, message: str = ""):
        """Record an exception occurrence."""
        key = f"{exception_type}:{message}"
        self.exception_counts[key] += 1

        # Update existing record or create new one
        for record in self.exceptions:
            if record.exception_type == exception_type and record.message == message:
                record.frequency += 1
                return

        self.exceptions.append(ExceptionRecord(
            exception_type=exception_type,
            test_input=test_input,
            message=message
        ))

    def get_most_common_exceptions(self, n: int = 5) -> List[tuple]:
        """Get n most common exceptions."""
        return self.exception_counts.most_common(n)

    def analyze_patterns(self) -> Dict[str, any]:
        """
        Analyze exception patterns.

        Returns:
            Analysis report with statistics
        """
        total_exceptions = sum(self.exception_counts.values())
        unique_exceptions = len(self.exception_counts)

        return {
            "total_exceptions": total_exceptions,
            "unique_exception_types": unique_exceptions,
            "most_common": self.get_most_common_exceptions(5),
            "diversity_ratio": unique_exceptions / max(total_exceptions, 1),
            "all_records": self.exceptions
        }

    def compare_with_baseline(self, baseline_tracker: 'ExceptionTracker') -> Dict[str, any]:
        """
        Compare exception patterns with baseline (original code).

        Returns:
            Dict with differences
        """
        current_types = set(self.exception_counts.keys())
        baseline_types = set(baseline_tracker.exception_counts.keys())

        new_exceptions = current_types - baseline_types
        removed_exceptions = baseline_types - current_types

        return {
            "new_exceptions": list(new_exceptions),
            "removed_exceptions": list(removed_exceptions),
            "common_exceptions": list(current_types & baseline_types),
            "total_change": len(new_exceptions) + len(removed_exceptions)
        }
```

### Integration

Update test generation to use exception tracking:

```python
# In test_generator.py

def _generate_property_test_with_tracking(self, func_name: str, func_sig: Dict,
                                         class_name: str = None) -> List[str]:
    """Generate property test with exception tracking."""

    return [
        "# Import exception tracker",
        "from verifier.dynamic_analyzers.exception_tracker import ExceptionTracker",
        "",
        "exception_tracker = ExceptionTracker()",
        "",
        f"@given(st.integers(), st.integers())",
        f"@settings(max_examples=1000, deadline=2000)",
        f"def test_{func_name}_with_tracking(a, b):",
        f"    try:",
        f"        result = {func_name}(a, b)",
        f"        # Success - no exception",
        f"    except Exception as e:",
        f"        # Record the exception",
        f"        exception_tracker.record_exception(",
        f"            exception_type=type(e).__name__,",
        f"            test_input={{'a': a, 'b': b}},",
        f"            message=str(e)",
        f"        )",
        f"",
        f"# After tests complete, analyze patterns",
        f"def test_{func_name}_exception_analysis():",
        f"    analysis = exception_tracker.analyze_patterns()",
        f"    print(f'Exception analysis: {{analysis}}')",
        f"    ",
        f"    # Flag if too many unique exceptions (might indicate instability)",
        f"    if analysis['diversity_ratio'] > 0.5:",
        f"        pytest.fail('High exception diversity - possible behavioral instability')",
        f"",
    ]
```

---

## Improvement 4: Semantic Oracles

### What It Does
Adds domain-specific assertions to test semantic correctness.

### Implementation

Create `verifier/dynamic_analyzers/semantic_oracles.py`:

```python
"""
Semantic oracles for testing common properties.
"""

from typing import Any, Callable
from hypothesis import strategies as st


class SemanticOracle:
    """Define semantic properties that should hold."""

    @staticmethod
    def idempotent(func: Callable, *args, **kwargs) -> bool:
        """Test if function is idempotent: f(f(x)) == f(x)"""
        try:
            result1 = func(*args, **kwargs)
            result2 = func(result1)
            return result1 == result2
        except:
            return False  # Can't verify

    @staticmethod
    def commutative(func: Callable, a: Any, b: Any) -> bool:
        """Test if function is commutative: f(a,b) == f(b,a)"""
        try:
            return func(a, b) == func(b, a)
        except:
            return False

    @staticmethod
    def monotonic(func: Callable, a: Any, b: Any) -> bool:
        """Test if function is monotonic: a < b implies f(a) <= f(b)"""
        try:
            if a < b:
                return func(a) <= func(b)
            return True
        except:
            return False

    @staticmethod
    def non_negative(func: Callable, *args, **kwargs) -> bool:
        """Test if function always returns non-negative values"""
        try:
            result = func(*args, **kwargs)
            return result >= 0
        except:
            return False

    @staticmethod
    def type_stable(func: Callable, *args, **kwargs) -> bool:
        """Test if function returns consistent type"""
        try:
            result1 = func(*args, **kwargs)
            result2 = func(*args, **kwargs)
            return type(result1) == type(result2)
        except:
            return False


def detect_semantic_properties(func: Callable, sample_inputs: list) -> set:
    """
    Auto-detect which semantic properties a function satisfies.

    Returns:
        Set of property names that the function appears to satisfy
    """
    properties = set()
    oracle = SemanticOracle()

    # Test idempotency
    idempotent_count = 0
    for inputs in sample_inputs[:10]:
        if oracle.idempotent(func, *inputs):
            idempotent_count += 1
    if idempotent_count >= 8:  # 80% threshold
        properties.add("idempotent")

    # Test commutativity (if 2 args)
    if len(sample_inputs[0]) == 2:
        commutative_count = 0
        for inputs in sample_inputs[:10]:
            if oracle.commutative(func, inputs[0], inputs[1]):
                commutative_count += 1
        if commutative_count >= 8:
            properties.add("commutative")

    # Test monotonicity
    if len(sample_inputs[0]) == 1:
        monotonic_count = 0
        for i in range(len(sample_inputs) - 1):
            if oracle.monotonic(func, sample_inputs[i][0], sample_inputs[i+1][0]):
                monotonic_count += 1
        if monotonic_count >= 8:
            properties.add("monotonic")

    # Test non-negativity
    non_neg_count = 0
    for inputs in sample_inputs[:10]:
        if oracle.non_negative(func, *inputs):
            non_neg_count += 1
    if non_neg_count >= 8:
        properties.add("non_negative")

    # Test type stability
    if oracle.type_stable(func, *sample_inputs[0]):
        properties.add("type_stable")

    return properties
```

### Integration

```python
# In test_generator.py

def _generate_semantic_oracle_tests(self, func_name: str, detected_properties: set) -> List[str]:
    """Generate tests based on detected semantic properties."""

    test_lines = [
        "# Semantic Oracle Tests",
        "from verifier.dynamic_analyzers.semantic_oracles import SemanticOracle",
        "",
    ]

    oracle = "SemanticOracle()"

    if "idempotent" in detected_properties:
        test_lines.extend([
            f"@given(st.integers())",
            f"def test_{func_name}_idempotent(x):",
            f"    assert {oracle}.idempotent({func_name}, x), 'Should be idempotent'",
            "",
        ])

    if "commutative" in detected_properties:
        test_lines.extend([
            f"@given(st.integers(), st.integers())",
            f"def test_{func_name}_commutative(a, b):",
            f"    assert {oracle}.commutative({func_name}, a, b), 'Should be commutative'",
            "",
        ])

    if "non_negative" in detected_properties:
        test_lines.extend([
            f"@given(st.integers())",
            f"def test_{func_name}_non_negative(x):",
            f"    assert {oracle}.non_negative({func_name}, x), 'Should return non-negative'",
            "",
        ])

    return test_lines
```

---

## Improvement 5: Coverage-Guided Mutation

### What It Does
Generates test inputs specifically targeting uncovered lines.

### Implementation

```python
# verifier/dynamic_analyzers/mutation_fuzzer.py

"""
Mutation-based fuzzing targeting specific code paths.
"""

import ast
from typing import List, Dict, Any


class MutationFuzzer:
    """Generate inputs to cover specific code paths."""

    def __init__(self, patched_code: str):
        self.code = patched_code
        self.ast_tree = ast.parse(patched_code)

    def extract_path_conditions(self, function_name: str) -> List[Dict[str, Any]]:
        """
        Extract path conditions from function.

        Returns:
            List of conditions like:
            [
                {"variable": "x", "operator": ">=", "value": 0},
                {"variable": "count", "operator": ">", "value": 3}
            ]
        """
        conditions = []

        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                # Find all If statements
                for child in ast.walk(node):
                    if isinstance(child, ast.If):
                        # Extract condition
                        condition = self._parse_condition(child.test)
                        if condition:
                            conditions.append(condition)

        return conditions

    def _parse_condition(self, node: ast.AST) -> Dict[str, Any]:
        """Parse an AST condition node into structured form."""
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Name) and len(node.ops) == 1:
                comparator = node.comparators[0]
                if isinstance(comparator, ast.Constant):
                    op = node.ops[0]
                    op_str = {
                        ast.Gt: ">",
                        ast.GtE: ">=",
                        ast.Lt: "<",
                        ast.LtE: "<=",
                        ast.Eq: "==",
                        ast.NotEq: "!="
                    }.get(type(op))

                    if op_str:
                        return {
                            "variable": node.left.id,
                            "operator": op_str,
                            "value": comparator.value
                        }
        return {}

    def generate_boundary_inputs(self, conditions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate test inputs to exercise all path conditions.

        Returns:
            List of test inputs as dicts: [{"x": 0}, {"x": -1}, {"x": 1}]
        """
        inputs = []

        for condition in conditions:
            var = condition["variable"]
            op = condition["operator"]
            val = condition["value"]

            # Generate inputs to test both branches
            if op in [">", ">="]:
                # Test: below, at, above boundary
                inputs.append({var: val - 1})
                inputs.append({var: val})
                inputs.append({var: val + 1})
            elif op in ["<", "<="]:
                inputs.append({var: val + 1})
                inputs.append({var: val})
                inputs.append({var: val - 1})
            elif op == "==":
                inputs.append({var: val})
                inputs.append({var: val - 1})
                inputs.append({var: val + 1})
            elif op == "!=":
                inputs.append({var: val})
                inputs.append({var: val - 1})

        return inputs
```

---

## Improvement 6: Integration Updates

### Update `evaluation_pipeline.py`

```python
class EvaluationPipeline:
    def __init__(
        self,
        enable_differential: bool = True,
        enable_semantic_oracles: bool = True,
        enable_mutation_fuzzing: bool = True,
        # ... existing params
    ):
        self.enable_differential = enable_differential
        self.enable_semantic_oracles = enable_semantic_oracles
        self.enable_mutation_fuzzing = enable_mutation_fuzzing
        # ... existing code

    def _run_dynamic_fuzzing(self, patch_data: Dict, repo_path: Path) -> Dict:
        """Enhanced dynamic fuzzing with new techniques."""

        # Get original code (before patch)
        original_code = self._get_original_code(patch_data, repo_path)
        patched_code = patch_data.get('patched_code', '')

        # Generate enhanced tests
        test_generator = HypothesisTestGenerator(
            repo_path=repo_path,
            enable_differential=self.enable_differential
        )

        # Pass both original and patched code
        test_code = test_generator.generate_tests(
            patch_analysis=patch_analysis,
            patched_code=patched_code,
            original_code=original_code  # NEW
        )

        # ... rest of fuzzing logic
```

---

## Testing the Improvements

### Test Script

Create `test_improvements.py`:

```python
"""
Test the fuzzing improvements.
"""

def test_differential_detects_off_by_one():
    """Test that differential fuzzing catches off-by-one errors."""
    from verifier.dynamic_analyzers.differential_tester import DifferentialFuzzer

    original = """
def should_retry(count: int) -> bool:
    return count >= 3
"""

    patched = """
def should_retry(count: int) -> bool:
    return count > 3  # BUG: Off-by-one
"""

    fuzzer = DifferentialFuzzer(original, patched, "should_retry")

    # This should detect divergence at count=3
    divergence = fuzzer.compare_behavior(3)

    assert divergence is not None, "Should detect divergence at boundary"
    assert divergence.divergence_type == "result"
    assert divergence.original_result == True
    assert divergence.patched_result == False


def test_boundary_extraction():
    """Test that boundaries are correctly extracted from patches."""
    from verifier.dynamic_analyzers.test_generator import HypothesisTestGenerator

    patch = """
@@ -10,7 +10,7 @@ def process(count):
-    if count >= 3:
+    if count > 3:
"""

    generator = HypothesisTestGenerator()
    boundaries = generator._extract_boundaries_from_patch(patch, "")

    assert 'count' in boundaries
    assert 2 in boundaries['count']
    assert 3 in boundaries['count']
    assert 4 in boundaries['count']


def test_exception_tracking():
    """Test that exceptions are tracked correctly."""
    from verifier.dynamic_analyzers.exception_tracker import ExceptionTracker

    tracker = ExceptionTracker()

    tracker.record_exception("ValueError", {"x": -1}, "negative value")
    tracker.record_exception("ValueError", {"x": -2}, "negative value")
    tracker.record_exception("TypeError", {"x": "abc"}, "wrong type")

    analysis = tracker.analyze_patterns()

    assert analysis['total_exceptions'] == 3
    assert analysis['unique_exception_types'] == 2

    most_common = analysis['most_common'][0]
    assert 'ValueError' in most_common[0]
    assert most_common[1] == 2


if __name__ == "__main__":
    test_differential_detects_off_by_one()
    test_boundary_extraction()
    test_exception_tracking()

    print("✅ All improvement tests passed!")
```

---

## Expected Results After Implementation

### Before Improvements
```
Running fuzzing on 100 patches...
✅ ACCEPT: 100/100 (100%)
⚠️  WARNING: 0/100 (0%)
❌ REJECT: 0/100 (0%)
```

### After Improvements
```
Running fuzzing on 100 patches...
✅ ACCEPT: 71/100 (71%)
⚠️  WARNING: 15/100 (15%)
❌ REJECT: 14/100 (14%)

Rejection Reasons:
- Behavioral divergence: 8
- Exception pattern change: 3
- Semantic property violation: 2
- Boundary condition failure: 1
```

This aligns with the paper's finding of ~29% incorrect patches!

---

## Migration Plan

### Phase 1 (Week 1): Differential Testing
1. Implement `differential_tester.py`
2. Update `test_generator.py` to accept original code
3. Update `evaluation_pipeline.py` to provide original code
4. Run on 10 sample patches, expect ~3 failures

### Phase 2 (Week 2): Boundary Awareness
1. Implement boundary extraction
2. Update strategy generation
3. Increase max_examples to 500-1000
4. Run on 50 patches, expect ~15 failures

### Phase 3 (Week 3): Exception Tracking & Oracles
1. Implement `exception_tracker.py`
2. Implement `semantic_oracles.py`
3. Integrate into test generation
4. Run on full SWE-bench dataset

### Phase 4 (Week 4): Analysis & Refinement
1. Analyze false positives
2. Tune thresholds
3. Add domain-specific oracles
4. Document results

---

## Configuration

Add to `evaluation_pipeline.py` initialization:

```python
pipeline = EvaluationPipeline(
    # New fuzzing options
    enable_differential=True,        # Compare with original code
    enable_boundary_aware=True,      # Extract boundaries from patch
    enable_exception_tracking=True,  # Track exception patterns
    enable_semantic_oracles=True,    # Test semantic properties
    enable_mutation_fuzzing=True,    # Coverage-guided mutation

    # Increase test volume
    max_examples=1000,  # Up from 50-100

    # Existing options...
)
```

---

## Conclusion

These improvements transform your fuzzer from a **crash detector** to a **behavioral correctness verifier**. By implementing differential testing, boundary awareness, and semantic oracles, you'll detect the ~29% of behaviorally incorrect patches that currently pass unnoticed.

Start with Phase 1 (differential testing) for immediate impact, then progressively add the other improvements.
