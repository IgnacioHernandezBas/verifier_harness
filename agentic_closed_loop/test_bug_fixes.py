#!/usr/bin/env python3
"""
Test script to validate the 3 critical bug fixes.

Run with: python -m agentic_closed_loop.test_bug_fixes
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_closed_loop import diagnostics
from agentic_closed_loop.pattern_detector import detect_internal_import_attempt


def test_bug1_misclassification_fix():
    """
    Test Bug #1: Misclassification of Import Errors

    Previously, any ImportError with "_pytest" in the stack trace was classified
    as "internal_import_error", even when the test code didn't have internal imports.

    Now it should correctly identify the real issue.
    """
    print("\n" + "="*60)
    print("TEST 1: Bug #1 - Misclassification Fix")
    print("="*60)

    # Simulate django-16255 error: cannot import 'get_latest_lastmod'
    bug_output = {
        "status": "ERROR",
        "stdout": """============================= test session starts ==============================
platform linux -- Python 3.9.20, pytest-8.4.2, pluggy-1.6.0
==================================== ERRORS ====================================
_ ERROR collecting claim_tests/django__django-16255/django__django_16255__test_claim_c1.py _
ImportError while importing test module '/workspace/claim_tests/django__django-16255/django__django_16255__test_claim_c1.py'.
Traceback:
.pip_packages/_pytest/python.py:498: in importtestmodule
    mod = import_path(
claim_tests/django__django-16255/django__django_16255__test_claim_c1.py:2: in <module>
    from django.contrib.sitemaps import Sitemap, get_latest_lastmod
E   ImportError: cannot import name 'get_latest_lastmod' from 'django.contrib.sitemaps'
""",
        "stderr": ""
    }

    gold_output = {
        "status": "ERROR",
        "stdout": bug_output["stdout"],
        "stderr": ""
    }

    # Test code WITHOUT internal imports
    generated_code = """import pytest
from django.contrib.sitemaps import Sitemap, get_latest_lastmod

def test_claim_c1():
    pass
"""

    # Should NOT classify as internal_import_error since code doesn't have internal imports
    label, details = diagnostics._classify_pair(bug_output, gold_output, generated_code)

    print(f"Classification: {label}")
    print(f"Details preview: {details[:200]}...")

    if label == "internal_import_error":
        print("❌ FAILED: Still misclassifying as internal_import_error")
        print("   The test code doesn't have internal imports!")
        return False
    elif label == "import_error":
        print("✅ PASSED: Correctly classified as import_error")
        if "cannot import" in details and "get_latest_lastmod" in details:
            print("✅ PASSED: Details contain helpful guidance")
            return True
        else:
            print("⚠️  WARNING: Details could be more helpful")
            return True
    else:
        print(f"⚠️  UNEXPECTED: Got label '{label}' (expected import_error)")
        return False


def test_bug1_actual_internal_import():
    """
    Test that actual internal imports are still detected correctly.
    """
    print("\n" + "="*60)
    print("TEST 2: Bug #1 - Still Detects Real Internal Imports")
    print("="*60)

    bug_output = {
        "status": "ERROR",
        "stdout": """============================= test session starts ==============================
==================================== ERRORS ====================================
_ ERROR collecting test.py _
ImportError: cannot import name 'TempdirFactory' from '_pytest.tmpdir'
""",
        "stderr": ""
    }

    gold_output = {"status": "ERROR", "stdout": bug_output["stdout"], "stderr": ""}

    # Test code WITH internal imports
    generated_code = """import pytest
from _pytest.tmpdir import TempdirFactory

def test_claim_c1():
    pass
"""

    label, details = diagnostics._classify_pair(bug_output, gold_output, generated_code)

    print(f"Classification: {label}")

    if label == "internal_import_error":
        print("✅ PASSED: Correctly detected internal import in test code")
        return True
    else:
        print(f"❌ FAILED: Should classify as internal_import_error, got '{label}'")
        return False


def test_bug2_pattern_detection():
    """
    Test Bug #2: Pattern Detection is now used.

    Verify that detect_internal_import_attempt correctly identifies patterns.
    """
    print("\n" + "="*60)
    print("TEST 3: Bug #2 - Pattern Detection Works")
    print("="*60)

    # Test 1: Code with internal import
    code_with_internal = """import pytest
from _pytest.tmpdir import TempdirFactory

def test_foo():
    pass
"""

    result = detect_internal_import_attempt(code_with_internal)
    if result and result.get("pattern") == "internal_import":
        print("✅ PASSED: Detected 'from _pytest.tmpdir import TempdirFactory'")
        print(f"   Found: {result}")
    else:
        print("❌ FAILED: Should detect internal import pattern")
        return False

    # Test 2: Code without internal import
    code_without_internal = """import pytest
from django.contrib.sitemaps import Sitemap

def test_foo():
    pass
"""

    result = detect_internal_import_attempt(code_without_internal)
    if result is None:
        print("✅ PASSED: Correctly found no internal imports in clean code")
    else:
        print(f"❌ FAILED: False positive - detected pattern when there isn't one: {result}")
        return False

    return True


def test_bug3_early_exit():
    """
    Test Bug #3: Early exit for repetitive failures.

    This is tested by verifying the logic in orchestrator._should_exit.
    """
    print("\n" + "="*60)
    print("TEST 4: Bug #3 - Early Exit Logic")
    print("="*60)

    # Simulate state with 3 identical internal_import_errors
    state = {
        "attempts": [
            {"failure_classification": {"label": "internal_import_error"}},
            {"failure_classification": {"label": "internal_import_error"}},
            {"failure_classification": {"label": "internal_import_error"}},
        ]
    }

    # Import and test orchestrator logic
    from agentic_closed_loop.orchestrator import LoopOrchestrator

    # Create a minimal orchestrator instance
    orchestrator = LoopOrchestrator(
        state_file=Path("/tmp/test_state.json"),
        instance_id="test",
        claim_id="C1",
        max_attempts=10,
        singularity_image=None,
        conda_env="test",
        common_args=[],
        auto_detect_container=False
    )

    exit_decision = orchestrator._should_exit(state, attempt=3)

    print(f"Exit decision: {exit_decision}")

    if exit_decision["should_exit"]:
        print("✅ PASSED: Would exit after 3 identical internal_import_errors")
        if "stuck_in_loop" in exit_decision["reason"]:
            print("✅ PASSED: Reason correctly identifies stuck loop")
            return True
        else:
            print("⚠️  WARNING: Exit reason doesn't mention stuck loop")
            return True
    else:
        print("❌ FAILED: Should exit after 3 identical errors")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("CRITICAL BUG FIX VALIDATION TESTS")
    print("="*70)

    tests = [
        ("Bug #1: Misclassification Fix", test_bug1_misclassification_fix),
        ("Bug #1: Real Internal Imports", test_bug1_actual_internal_import),
        ("Bug #2: Pattern Detection", test_bug2_pattern_detection),
        ("Bug #3: Early Exit", test_bug3_early_exit),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Fixes are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
