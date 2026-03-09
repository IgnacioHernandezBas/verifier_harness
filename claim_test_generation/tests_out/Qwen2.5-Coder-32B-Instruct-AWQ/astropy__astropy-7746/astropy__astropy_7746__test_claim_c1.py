# Checklist TODO: Test passes with empty inputs.
# Checklist TODO: Result contains two empty arrays.
# Checklist TODO: Arrays have dtype float64 and size 0.
import pytest
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

def test_claim_c1():
    # Given: A WCS object is created with a valid FITS file.
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        w = WCS(f[0].header)

    # When: wcs.wcs_pix2world([], [], 0) is called
    result = w.wcs_pix2world([], [], 0)

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    # Result is a list of two empty arrays.
    assert isinstance(result, list)
    assert len(result) == 2

    # Each array in the result has a size of 0.
    assert result[0].size == 0
    assert result[1].size == 0

    # The dtype of each array in the result is float64.
    assert result[0].dtype == np.float64
    assert result[1].dtype == np.float64
