import pytest
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

def test_claim_c1(capsys):
    # Given: A WCS object and empty input lists/arrays
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        wcs = WCS(f[0].header)

    # When: Calling wcs_pix2world with empty lists/arrays as pixel coordinates
    result = wcs.wcs_pix2world([], [], 0)

    # Then: Returns empty outputs (empty sequences or arrays with size==0) without raising InconsistentAxisTypesError
    # Checklist:
    # Test passes without raising InconsistentAxisTypesError
    # Result is a list of two empty arrays with dtype=float64
    # Test handles edge cases correctly

    # Assertions
    # Returns empty outputs (empty sequences or arrays with size==0)
    assert len(result) == 2
    assert result[0].size == 0
    assert result[1].size == 0

    # Does not raise InconsistentAxisTypesError
    # (Implicitly checked by not raising an exception)

    # Result is a list of two empty arrays with dtype=float64
    assert isinstance(result, list)
    assert isinstance(result[0], np.ndarray)
    assert isinstance(result[1], np.ndarray)
    assert result[0].dtype == np.float64
    assert result[1].dtype == np.float64

    # Test handles edge cases correctly
    # (Implicitly checked by not raising an exception)
