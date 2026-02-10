#!/usr/bin/env python3
"""
Test script to verify guardrail probe logic fixes.
"""
import sys
import inspect
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from agentic_closed_loop.guardrails import _execute_probe


# Test cases
class MockResponse:
    """Mock class to test instance methods."""

    def iter_content(self, chunk_size=1, decode_unicode=False):
        """Instance method with self and optional params."""
        return iter([b"test"])

    @classmethod
    def from_dict(cls, data):
        """Class method with cls."""
        return cls()

    @staticmethod
    def parse(text):
        """Static method, no self/cls."""
        return text


def standalone_function(arg1, arg2="default"):
    """Function with required and optional params."""
    return arg1


def no_arg_function():
    """Function with no required params."""
    return "success"


def test_probe_logic():
    """Test the probe logic with various callable types."""

    print("=" * 70)
    print("TESTING GUARDRAIL PROBE LOGIC")
    print("=" * 70)

    test_cases = [
        # (name, callable, expected_pass, should_contain_text)
        ("Instance method (iter_content)", MockResponse.iter_content, True, "Instance/class method"),
        ("Class method (from_dict)", MockResponse.from_dict, True, "non-trivial inputs"),  # cls stripped, but still skipped
        ("Static method (parse)", MockResponse.parse, True, "non-trivial inputs"),
        ("Function with required arg", standalone_function, True, "non-trivial inputs"),
        ("Function with no args", no_arg_function, True, "Probe succeeded"),
    ]

    passed_all = True

    for name, func, expected_pass, should_contain in test_cases:
        probe_ok, message = _execute_probe(name, func)

        status = "✓ PASS" if probe_ok == expected_pass else "✗ FAIL"
        contains_check = "✓" if should_contain.lower() in message.lower() else "✗"

        print(f"\n{status} | {name}")
        print(f"  Expected: {expected_pass}, Got: {probe_ok}")
        print(f"  Message: {message}")
        print(f"  {contains_check} Contains '{should_contain}': {should_contain.lower() in message.lower()}")

        if probe_ok != expected_pass or should_contain.lower() not in message.lower():
            passed_all = False

    print("\n" + "=" * 70)
    if passed_all:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)

    return passed_all


if __name__ == "__main__":
    success = test_probe_logic()
    sys.exit(0 if success else 1)
