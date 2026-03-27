# Checklist TODO: Test confirms no exception during WCS transformation with empty inputs.
# Checklist TODO: WCS object is correctly initialized from FITS file.
# Checklist TODO: Function returns without raising InconsistentAxisTypesError.
import pytest
import numpy as np
from astropy.wcs import WCS
from astropy.wcs import InconsistentAxisTypesError

def test_claim_c2():
    # Given: A WCS object with naxis=2
    wcs = WCS(naxis=2)
    wcs.crpix = [0, 0]
    wcs.cdelt = [1, 1]
    wcs.crval = [0, 0]
    wcs.ctype = ['RA', 'DEC']
    
    # Empty input arrays
    empty_inputs = (np.array([], dtype=float), np.array([], dtype=float))
    
    # When: Execute WCS transformation with empty inputs
    # Then: No InconsistentAxisTypesError is raised
    result = wcs.all_pix2world(*empty_inputs, 0)
    
    # Check output is a tuple of empty arrays
    assert all(len(arr) == 0 for arr in result)
