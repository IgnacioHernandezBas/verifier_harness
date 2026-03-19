# Checklist TODO: WCS instance initialized from FITS file
# Checklist TODO: Empty inputs produce empty outputs
# Checklist TODO: Third argument (0) is properly handled
import pytest
import numpy as np
from astropy.wcs import WCS

def _is_empty(x):
    return len(x) == 0 or (isinstance(x, np.ndarray) and x.size == 0)

def test_claim_c1(tmpdir):
    # Given: WCS instance with minimal valid configuration
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crpix = [0, 0]
    wcs.wcs.cdelt = [1, 1]
    wcs.wcs.crval = [0, 0]

    # When: Call with empty lists
    result1 = wcs.wcs_pix2world([], [], 0)
    result2 = wcs.wcs_pix2world(np.array([]), np.array([]), 0)

    # Then: Verify empty outputs
    assert all(_is_empty(arr) for arr in result1)
    assert all(_is_empty(arr) for arr in result2)

    # Edge case: Mixed input types
    result3 = wcs.wcs_pix2world([], np.array([]), 0)
    assert all(_is_empty(arr) for arr in result3)
