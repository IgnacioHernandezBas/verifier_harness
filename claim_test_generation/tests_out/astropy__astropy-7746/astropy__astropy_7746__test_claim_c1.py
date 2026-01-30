import pytest
from astropy.wcs import WCS

def _is_empty(x):
    return len(x) == 0 if isinstance(x, list) else x.size == 0

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
    assert _is_empty(result[0])
    assert _is_empty(result[1])
