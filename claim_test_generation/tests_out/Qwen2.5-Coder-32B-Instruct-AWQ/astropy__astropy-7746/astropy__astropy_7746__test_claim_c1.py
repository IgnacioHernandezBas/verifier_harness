# Checklist TODO: Test passes with empty inputs.
# Checklist TODO: Result contains two empty arrays.
# Checklist TODO: Arrays have dtype float64.
import pytest
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

def test_claim_c1():
    # Given: A WCS object is created with a valid FITS file.
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        w = WCS(f[0].header)

    # When: wcs.wcs_pix2world([], [], 0) is called
    result_list = w.wcs_pix2world([], [], 0)

    # Then: Result is a list of two empty arrays.
    assert isinstance(result_list, list)
    assert len(result_list) == 2

    # Then: Each array in the result has a size of 0.
    assert result_list[0].size == 0
    assert result_list[1].size == 0

    # Then: The dtype of each array in the result is float64.
    assert result_list[0].dtype == np.float64
    assert result_list[1].dtype == np.float64
