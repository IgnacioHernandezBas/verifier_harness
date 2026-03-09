# Checklist TODO: Test must use a valid FITS file to initialize WCS.
# Checklist TODO: Test must call wcs_pix2world with empty inputs.
# Checklist TODO: Test must verify the output is empty and no exceptions are raised.
import pytest
from astropy.wcs import WCS
from astropy.io import fits
import numpy as np

def test_claim_c1(tmpdir, monkeypatch):
    # Given: A WCS object is created with a valid FITS file.
    # Create a temporary FITS file with valid content.
    temp_fits_file = tmpdir.join('temp.fits')
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        f.writeto(temp_fits_file)
    
    # Use monkeypatch to make the temporary FITS file accessible.
    monkeypatch.setattr(fits, 'open', lambda x: fits.open(temp_fits_file))
    
    with fits.open(temp_fits_file) as f:
        w = WCS(f[0].header)
    
    # When: wcs.wcs_pix2world([], [], 0) is called
    result = w.wcs_pix2world([], [], 0)
    
    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    assert isinstance(result, (list, tuple))
    assert len(result) == 2
    assert len(result[0]) == 0
    assert len(result[1]) == 0

    # Edge cases
    # Test with None instead of empty lists.
    with pytest.raises(TypeError):
        w.wcs_pix2world(None, None, 0)
    
    # Test with different types of empty inputs (e.g., numpy arrays).
    result = w.wcs_pix2world(np.array([]), np.array([]), 0)
    assert isinstance(result, (list, tuple))
    assert len(result) == 2
    assert len(result[0]) == 0
    assert len(result[1]) == 0
    
    # Test with a non-zero third parameter.
    result = w.wcs_pix2world([], [], 1)
    assert isinstance(result, (list, tuple))
    assert len(result) == 2
    assert len(result[0]) == 0
    assert len(result[1]) == 0
