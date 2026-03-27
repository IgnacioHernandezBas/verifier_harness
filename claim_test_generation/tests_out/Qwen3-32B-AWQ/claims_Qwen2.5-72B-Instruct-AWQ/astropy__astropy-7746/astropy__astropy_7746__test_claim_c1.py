# Checklist TODO: Function returns empty sequences when given empty inputs.
# Checklist TODO: Handles list and array input types consistently.
# Checklist TODO: Output count matches WCS world coordinate dimensions.
import pytest
from astropy.wcs import WCS
import numpy as np

def test_claim_c1(tmpdir):
    # Given: Create a minimal WCS instance with naxis=2
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crpix = [0, 0]
    wcs.wcs.cdelt = [1, 1]
    wcs.wcs.crval = [0, 0]

    # When: Call wcs_pix2world with empty lists
    result = wcs.wcs_pix2world([], [], 0)

    # Then: Verify output sequences/arrays have length/size 0
    for arr in result:
        assert len(arr) == 0 or (hasattr(arr, 'size') and arr.size == 0)

    # Edge case: Test with empty NumPy arrays
    result = wcs.wcs_pix2world(np.array([]), np.array([]), 0)
    for arr in result:
        assert arr.size == 0

    # Ensure output count matches WCS world coordinate dimensions
    assert len(result) == wcs.naxis
