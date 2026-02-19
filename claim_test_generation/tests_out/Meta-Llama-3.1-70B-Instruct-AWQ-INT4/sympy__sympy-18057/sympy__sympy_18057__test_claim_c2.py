import pytest
from sympy import Symbol

def test_claim_c2(capsys):
    # Given: An unknown object whose repr is 'x'
    class C:
        def __repr__(self):
            return 'x.y'

    # When: Calling sympy.Symbol('x') == C()
    # Then: Returns False
    # Test passes without raising an AttributeError
    assert not hasattr(Symbol('x'), 'y')

    # Test correctly returns False when comparing sympy.Symbol('x') with an object whose repr is 'x.y'
    assert Symbol('x') != C()

    # Test correctly handles edge cases
    # Compare with an object whose repr is not 'x.y'
    class D:
        def __repr__(self):
            return 'x'
    assert Symbol('x') != D()

    # Compare with a sympy.Symbol that is not 'x'
    assert Symbol('x') != Symbol('y')

    # Compare with an object that is not a sympy.Symbol
    assert Symbol('x') != 1

    # Capture stdout and stderr to ensure no unexpected output
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err
