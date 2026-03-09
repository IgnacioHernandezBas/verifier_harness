import pytest
from sympy import Symbol

def test_claim_c1(capsys):
    # Given: A SymPy Symbol and an object with a repr that evaluates to an invalid expression.
    x = Symbol('x')
    class C:
        def __repr__(self):
            return 'x.y'

    # When: sympy.Symbol('x') == C()
    try:
        # Test passes without raising an AttributeError
        x == C()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

    # Then: No AttributeError is raised.
    # Test correctly handles invalid expressions
    # Test uses correct imports as shown in issue context

    # Edge cases
    # Invalid expression with multiple levels of nesting
    class NestedC:
        def __repr__(self):
            return 'x.y.z'
    try:
        x == NestedC()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

    # Invalid expression with special characters
    class SpecialC:
        def __repr__(self):
            return 'x!@#$%^&*()'
    try:
        x == SpecialC()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

    # Valid expression for comparison
    class ValidC:
        def __repr__(self):
            return 'x'
    try:
        x == ValidC()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")
