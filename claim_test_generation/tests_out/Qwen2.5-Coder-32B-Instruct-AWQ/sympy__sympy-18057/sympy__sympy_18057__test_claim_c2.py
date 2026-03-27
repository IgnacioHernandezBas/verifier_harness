import pytest
from sympy import Symbol

# Define a custom class C with __repr__ returning 'x'
class C:
    def __repr__(self):
        return 'x'

# Define a custom class D with __repr__ not matching 'x'
class D:
    def __repr__(self):
        return 'y'

# Define a custom class E with __repr__ matching 'x' but different type
class E:
    def __repr__(self):
        return 'x'

# Create an instance of sympy.Symbol('x')
symbol_x = Symbol('x')

# Create an instance of C
c_instance = C()

# Create an instance of D
d_instance = D()

# Create an instance of E
e_instance = E()

def test_claim_c2():
    # Given: A custom class C with __repr__ returning 'x'
    # When: Calling __eq__ between sympy.Symbol('x') and C()
    # Then: Returns False
    assert (symbol_x == c_instance) is False  # Test fails if __eq__ returns True
    assert (symbol_x != c_instance) is True   # Test passes if __eq__ returns False

    # Ensure custom class does not inherit from sympy classes
    assert not isinstance(c_instance, Symbol)
    assert not isinstance(d_instance, Symbol)
    assert not isinstance(e_instance, Symbol)

    # Additional checks for edge cases
    # Custom class with __repr__ not matching 'x'
    assert (symbol_x == d_instance) is False
    assert (symbol_x != d_instance) is True

    # Custom class with __repr__ matching 'x' but different type
    assert (symbol_x == e_instance) is False
    assert (symbol_x != e_instance) is True
