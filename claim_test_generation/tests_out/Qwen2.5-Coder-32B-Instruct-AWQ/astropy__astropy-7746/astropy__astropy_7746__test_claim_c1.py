# Checklist TODO: Test passes with empty lists.
# Checklist TODO: Test passes with empty arrays.
# Checklist TODO: Output size is verified to be 0.
import pytest
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

def test_claim_c1():
    # Create an instance of WCS using a valid FITS file.
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        w = WCS(f[0].header)

    # Prepare empty lists and arrays as input for wcs_pix2world.
    empty_list = []
    empty_array = np.array([])

    # Test with empty lists.
    # Given: An instance of WCS with a valid FITS file.
    # When: Calling wcs_pix2world with empty lists as input.
    # Then: Returns empty outputs (empty sequences OR arrays with size==0).
    result_list = w.wcs_pix2world(empty_list, empty_list, 0)
    # Output is an empty list.
    assert isinstance(result_list, list)
    # Output size is verified to be 0.
    assert len(result_list) == 0

    # Test with empty arrays.
    # Given: An instance of WCS with a valid FITS file.
    # When: Calling wcs_pix2world with empty arrays as input.
    # Then: Returns empty outputs (empty sequences OR arrays with size==0).
    result_array = w.wcs_pix2world(empty_array, empty_array, 0)
    # Output is an empty array.
    assert isinstance(result_array, np.ndarray)
    # Output size is verified to be 0.
    assert result_array.size == 0

    # Test with different dimensions of empty arrays.
    # Given: An instance of WCS with a valid FITS file.
    # When: Calling wcs_pix2world with different dimensions of empty arrays as input.
    # Then: Returns empty outputs (empty sequences OR arrays with size==0).
    empty_array_2d = np.array([[]])
    result_array_2d = w.wcs_pix2world(empty_array_2d, empty_array_2d, 0)
    # Output is an empty array.
    assert isinstance(result_array_2d, np.ndarray)
    # Output size is verified to be 0.
    assert result_array_2d.size == 0
