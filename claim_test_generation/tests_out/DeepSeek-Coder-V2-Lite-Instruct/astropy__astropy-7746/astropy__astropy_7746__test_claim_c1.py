# Checklist TODO: The function wcs_pix2world returns an empty list or array when passed empty lists/arrays.
# Checklist TODO: The function correctly handles the input parameters.
# Checklist TODO: The function behaves as expected with the given inputs.
import pytest
from astropy.wcs import WCS
from astropy.io import fits
from astropy.utils.data import get_pkg_data_filename
import numpy as np

@pytest.fixture
def wcs_object():
    with fits.open(get_pkg_data_filename('data/sip.fits')) as f:
        return WCS(f[0].header)

def test_claim_c1(wcs_object):
    # Given: A WCS object is created with a valid FITS file.
    wcs = wcs_object

    # When: wcs.wcs_pix2world([], [], 0) is called
    result = wcs.wcs_pix2world([], [], 0)

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    assert isinstance(result, tuple) and all(len(arr) == 0 for arr in result)

    # Check if the function correctly handles the input parameters.
    with pytest.raises(ValueError):
        wcs.wcs_pix2world(None, None, 0)

    # Ensure that the function behaves as expected with the given inputs.
    result = wcs.wcs_pix2world([[1, 2], [3, 4]], [1, 2], 0)
    assert isinstance(result, tuple) and all(len(arr) == 2 for arr in result)
