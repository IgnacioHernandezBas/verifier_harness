# Checklist TODO: Test passes when empty inputs return empty outputs
# Checklist TODO: No exceptions raised for empty inputs
# Checklist TODO: Verifies core transformation behavior, not implementation details
import pytest
import numpy as np
from astropy.wcs import WCS

def test_claim_c1():
    # GIVEN: Create a minimal WCS object with 2 axes
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crpix = [0.0, 0.0]
    wcs.wcs.cdelt = [1.0, 1.0]
    wcs.wcs.crval = [0.0, 0.0]

    # WHEN: Prepare empty inputs (numpy array and Python lists)
    empty_array = np.empty((0, 2))
    empty_list = [], []

    # THEN: Verify empty outputs without exceptions
    # Test with empty numpy array
    result_array = wcs.all_pix2world(empty_array, 0)
    assert result_array.size == 0  # Empty numpy array

    # Test with empty lists
    result_list = wcs.all_pix2world(*empty_list, 0)
    assert all(len(arr) == 0 for arr in result_list)  # Empty list of arrays
