# Checklist TODO: Import sympy and define class C with a specific repr.
# Checklist TODO: Create a Symbol and compare it with an instance of C.
# Checklist TODO: Ensure no AttributeError is raised during comparison.
import pytest
from sympy import Symbol

class C:
    def __repr__(self):
        return 'x.y'

def test_claim_c1(monkeypatch):
    # Given: A SymPy Symbol and an object with a repr that evaluates to an invalid expression.
    x = Symbol('x')
    c = C()

    # When: sympy.Symbol('x') == C()
    # Then: No AttributeError is raised.
    try:
        result = x == c
    except AttributeError as e:
        pytest.fail(f"AttributeError was raised: {e}")

    # Ensure no AttributeError is raised during comparison.
    assert result is False
