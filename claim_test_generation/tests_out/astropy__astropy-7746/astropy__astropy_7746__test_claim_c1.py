# Chosen strategy: unit
# Key observable(s) asserted: No exception raised, returns empty outputs
# Inputs/fixtures used: Minimal WCS object

import pytest
from astropy.wcs import WCS

def test_claim_c1():
    # Given: A WCS object is created with a valid FITS file.
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crpix = [1, 1]
    wcs.wcs.cdelt = [1, 1]
    wcs.wcs.crval = [0, 0]

    # When: wcs.wcs_pix2world([], [], 0) is called
    result = wcs.wcs_pix2world([], [], 0)

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    assert isinstance(result, tuple)
    assert all(len(r) == 0 for r in result)
