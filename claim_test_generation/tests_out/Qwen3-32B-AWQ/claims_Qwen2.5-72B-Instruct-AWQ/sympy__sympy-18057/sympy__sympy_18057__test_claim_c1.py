# Checklist TODO: Test confirms no AttributeError when comparing Symbol to C()
# Checklist TODO: Test uses exact import pattern 'import sympy' as per issue context
# Checklist TODO: Test verifies __eq__ handles non-Symbol objects safely
import pytest

def test_claim_c1():
    # Given: Create sympy Symbol 'x' and class C with __repr__ returning 'x.y'
    import sympy
    x = sympy.Symbol('x')
    class C:
        def __repr__(self):
            return 'x.y'
    c_instance = C()

    # When: Call __eq__ between Symbol and C instance
    result = x.__eq__(c_instance)

    # Then: No AttributeError raised, and __eq__ returns False
    assert result is False

    # Edge case: Object with __repr__ returning unrelated string
    class D:
        def __repr__(self):
            return 'abc'
    assert sympy.Symbol('x').__eq__(D()) is False

    # Edge case: Object without __repr__
    class E:
        pass
    assert sympy.Symbol('x').__eq__(E()) is False

    # Edge case: Object with __repr__ returning non-string
    class F:
        def __repr__(self):
            return 123
    assert sympy.Symbol('x').__eq__(F()) is False
