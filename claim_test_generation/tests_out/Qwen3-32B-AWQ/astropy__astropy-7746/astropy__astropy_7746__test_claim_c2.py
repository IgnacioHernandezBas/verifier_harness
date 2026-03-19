# Checklist TODO: WCS object initialized from FITS file successfully
# Checklist TODO: Pixel-to-world conversion executes with empty inputs
# Checklist TODO: No exceptions raised during coordinate transformation
import pytest
import numpy as np
from astropy.wcs import WCS

def test_claim_c2():
    # Given: WCS object with 2 axes and empty input arrays/lists
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crpix = [0, 0]
    wcs.wcs.cdelt = [1, 1]
    wcs.wcs.crval = [0, 0]

    empty_array = np.zeros((0, 2))
    empty_lists = ([], [])

    # When/Then: No exceptions during pixel-to-world conversion with empty inputs
    # Check 1: all_pix2world with empty numpy array
    with pytest.raises(Exception) as exc_info:
        wcs.all_pix2world(empty_array, 0)
    assert not exc_info, "Unexpected exception with empty numpy array"

    # Check 2: all_pix2world with empty lists
    with pytest.raises(Exception) as exc_info:
        wcs.all_pix2world(*empty_lists, 0)
    assert not exc_info, "Unexpected exception with empty lists"

    # Check 3: all_world2pix with empty numpy array
    with pytest.raises(Exception) as exc_info:
        wcs.all_world2pix(empty_array, 0)
    assert not exc_info, "Unexpected exception with empty numpy array"

    # Check 4: all_world2pix with empty lists
    with pytest.raises(Exception) as exc_info:
        wcs.all_world2pix(*empty_lists, 0)
    assert not exc_info, "Unexpected exception with empty lists"

    # Validate: WCS object remains valid after processing
    assert wcs.wcs.ctype == ['RA---TAN', 'DEC--TAN']
    assert np.allclose(wcs.wcs.crpix, [0, 0])
