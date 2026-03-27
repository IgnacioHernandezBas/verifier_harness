# Checklist TODO: Test confirms empty input returns empty output
# Checklist TODO: Test validates output type correctness
# Checklist TODO: Test ensures no exceptions for empty input
import pytest
import numpy as np
from astropy.wcs import WCS

def test_claim_c1():
    # Given: Create WCS instance with minimal setup
    wcs = WCS(naxis=2)
    # Test confirms empty input returns empty output
    result = wcs.wcs_pix2world([], [], 0)
    assert all(len(arr) == 0 for arr in result)
    # Verify output type correctness (numpy arrays)
    assert all(isinstance(arr, np.ndarray) for arr in result)
    # Ensure no exceptions raised for empty input
    # (implicitly tested by not raising exceptions)
    # Also test with empty numpy arrays
    empty_arr = np.array([])
    result = wcs.wcs_pix2world(empty_arr, empty_arr, 0)
    assert all(len(arr) == 0 for arr in result)
    assert all(isinstance(arr, np.ndarray) for arr in result)
