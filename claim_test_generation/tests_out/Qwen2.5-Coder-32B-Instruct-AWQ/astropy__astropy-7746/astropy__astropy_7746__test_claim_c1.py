# Checklist TODO: Test passes with empty inputs.
# Checklist TODO: Result contains empty arrays.
# Checklist TODO: No exceptions are raised.
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

    # Then: Result is a list of arrays with length 2.
    assert isinstance(result_list, list)
    assert len(result_list) == 2

    # Then: Each array in the result has size 0.
    for array in result_list:
        assert isinstance(array, np.ndarray)
        assert array.size == 0

    # Then: No exceptions are raised during the function call.
    # This is implicitly handled by the test not raising an exception.

    # Edge case: Check behavior with different origins (e.g., 1, -1).
    result_list_origin_1 = w.wcs_pix2world([], [], 1)
    assert isinstance(result_list_origin_1, list)
    assert len(result_list_origin_1) == 2
    for array in result_list_origin_1:
        assert isinstance(array, np.ndarray)
        assert array.size == 0

    result_list_origin_neg1 = w.wcs_pix2world([], [], -1)
    assert isinstance(result_list_origin_neg1, list)
    assert len(result_list_origin_neg1) == 2
    for array in result_list_origin_neg1:
        assert isinstance(array, np.ndarray)
        assert array.size == 0

    # Edge case: Test with non-empty but zero-length arrays.
    result_list_zero_length = w.wcs_pix2world(np.array([], dtype=float), np.array([], dtype=float), 0)
    assert isinstance(result_list_zero_length, list)
    assert len(result_list_zero_length) == 2
    for array in result_list_zero_length:
        assert isinstance(array, np.ndarray)
        assert array.size == 0

    # Edge case: Verify behavior with invalid FITS files or missing files.
    with pytest.raises((IOError, FileNotFoundError)):
        with fits.open('non_existent_file.fits') as f:
            w_invalid = WCS(f[0].header)
            w_invalid.wcs_pix2world([], [], 0)
