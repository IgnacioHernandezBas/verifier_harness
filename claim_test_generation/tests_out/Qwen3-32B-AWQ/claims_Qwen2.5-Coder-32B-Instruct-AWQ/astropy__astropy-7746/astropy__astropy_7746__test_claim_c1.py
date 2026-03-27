# Checklist TODO: WCS object initialized with valid FITS file
# Checklist TODO: Empty inputs produce empty outputs in wcs_pix2world
# Checklist TODO: Function handles empty sequences/arrays as documented
import pytest
from astropy.wcs import WCS
import numpy as np

def _is_empty(output):
    if hasattr(output, 'size'):
        return output.size == 0
    else:
        return len(output) == 0

def test_claim_c1():
    # Given: WCS object created with valid FITS file (simulated in code)
    wcs = WCS(naxis=2)
    wcs.crpix = [1, 1]
    wcs.cdelt = [1, 1]
    wcs.crval = [0, 0]
    wcs.ctype = ['RA', 'DEC']

    # When: wcs_pix2world is called with empty lists
    x_world, y_world = wcs.wcs_pix2world([], [], 0)

    # Then: returns empty outputs
    assert _is_empty(x_world)
    assert _is_empty(y_world)
