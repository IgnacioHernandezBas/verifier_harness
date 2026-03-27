# Checklist TODO: Test must use only public API methods.
# Checklist TODO: Test must provide empty inputs to the method.
# Checklist TODO: Test must verify no exceptions are raised.
import pytest
from astropy.wcs import WCS
from astropy.io import fits
import numpy as np

def test_claim_c2():
    # GIVEN: A WCS object and empty input lists/arrays
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        w = WCS(f[0].header)

    # WHEN: Executing WCS pixel-to-world coordinate conversion with empty inputs
    inp = np.zeros((0, 2))

    # THEN: No InconsistentAxisTypesError is raised during execution
    # Function returns expected output for empty inputs
    result = w.all_pix2world(inp, 0)
    assert_array_equal(inp, result)

    # THEN: Function does not raise any unexpected exceptions
    result = w.all_world2pix(inp, 0)
    assert_array_equal(inp, result)

    # Edge case: Test with None instead of empty list
    with pytest.raises(ValueError):
        w.all_pix2world(None, 0)

    # Edge case: Test with non-empty but invalid input shapes
    with pytest.raises(ValueError):
        w.all_pix2world(np.array([1, 2, 3]), 0)

    # Edge case: Test with a non-existent FITS file
    with pytest.raises(FileNotFoundError):
        with fits.open('non_existent.fits') as f:
            w = WCS(f[0].header)

# Helper function to assert array equality
def assert_array_equal(a, b):
    assert np.array_equal(a, b)
