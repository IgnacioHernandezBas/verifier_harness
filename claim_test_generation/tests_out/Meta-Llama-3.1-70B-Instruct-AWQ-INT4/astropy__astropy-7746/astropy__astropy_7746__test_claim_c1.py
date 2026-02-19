import pytest
from astropy.wcs import WCS
import numpy as np

def test_claim_c1(tmpdir, capsys):
    # Given: An instance of WCS with a valid FITS file
    # When: Calling wcs.wcs_pix2world with empty lists/arrays as input
    # Then: Returns empty outputs (empty sequences OR arrays with size==0)

    # Create a WCS instance with a valid FITS file
    # Pass empty lists/arrays as input to wcs.wcs_pix2world
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [1, 2]
    wcs.wcs.cdelt = [1, 1]
    wcs.wcs.crval = [1, 2]
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']

    # Test passes without raising an exception
    try:
        result = wcs.wcs_pix2world([], [], 0)
    except Exception as e:
        pytest.fail(f"Test raised an exception: {e}")

    # Output is a list of two empty arrays
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(x, np.ndarray) for x in result)

    # Each array has dtype float64
    assert all(x.dtype == np.float64 for x in result)

    # Each array is empty
    assert all(x.size == 0 for x in result)
