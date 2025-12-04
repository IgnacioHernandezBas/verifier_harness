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