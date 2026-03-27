import pytest
from sympy import Symbol

# Checklist: Test passes without raising AttributeError
# Checklist: Test correctly handles custom class with __repr__ method
# Checklist: Test correctly handles comparison between sympy.Symbol and custom object

def test_claim_c1(capsys):
    # Given: A custom class C with __repr__ returning 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'

    # When: Calling __eq__ between sympy.Symbol('x') and C()
    # Then: No AttributeError is raised during comparison
    try:
        _ = Symbol('x') == C()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

    # Edge case: Custom class C with __repr__ returning a different string
    class D:
        def __repr__(self):
            return 'a.b'

    try:
        _ = Symbol('x') == D()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

    # Edge case: Custom class C without __repr__ method
    class E:
        pass

    try:
        _ = Symbol('x') == E()
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

    # Edge case: Comparing sympy.Symbol('x') with a different object
    try:
        _ = Symbol('x') == 5
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")
