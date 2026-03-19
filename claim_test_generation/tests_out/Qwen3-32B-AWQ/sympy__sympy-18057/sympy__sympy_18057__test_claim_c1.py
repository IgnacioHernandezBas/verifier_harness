# Checklist TODO: Test confirms no exception during Symbol vs custom object comparison
# Checklist TODO: Assert comparison returns False as per correct behavior
# Checklist TODO: Verify __repr__ handling doesn't trigger attribute access
import pytest
from sympy import Symbol

def test_claim_c1():
    # Given: Custom class with __repr__ 'x.y'
    class C:
        def __repr__(self):
            return 'x.y'
    c = C()
    x = Symbol('x')

    # When: Comparing x == c
    result = x == c

    # Then: No exception raised and result is False
    assert result is False
