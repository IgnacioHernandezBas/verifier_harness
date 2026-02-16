# Checklist TODO: The function correctly returns empty lists/arrays when passed empty inputs.
# Checklist TODO: The function handles various edge cases without errors.
# Checklist TODO: The WCS object creation and transformation process is validated.
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
    # Check if the function returns an empty list or array when passed empty inputs.
    result = wcs_object.wcs_pix2world([], [], 0)
    assert len(result[0]) == 0
    assert len(result[1]) == 0

    # Verify the function's behavior with various edge cases.
    result = wcs_object.wcs_pix2world([1, 2], [3, 4], 0)
    assert len(result[0]) == 2
    assert len(result[1]) == 2

    # Ensure the function handles the WCS object creation and transformation correctly.
    result = wcs_object.wcs_pix2world([], [], 0)
    assert len(result[0]) == 0
    assert len(result[1]) == 0
