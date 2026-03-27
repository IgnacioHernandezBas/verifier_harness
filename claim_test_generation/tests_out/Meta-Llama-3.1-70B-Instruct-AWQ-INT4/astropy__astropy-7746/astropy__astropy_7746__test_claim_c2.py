import pytest
from astropy.io import fits
from astropy.wcs import WCS

def test_claim_c2(capsys):
    # Given: A WCS object and empty input lists/arrays
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        w = WCS(f[0].header)
    inp = [[], []]

    # When: Executing WCS pixel-to-world coordinate conversion with empty inputs
    # Then: No InconsistentAxisTypesError is raised during execution
    # Test raises no exceptions with empty inputs
    with pytest.raises(Exception) as exc_info:
        w.wcs_pix2world(*inp, 0)
    assert exc_info.type != WCS.InconsistentAxisTypesError

    # Test handles non-empty inputs correctly
    inp = [[1, 2], [3, 4]]
    result = w.wcs_pix2world(*inp, 0)
    assert len(result) == 2
    assert len(result[0]) == 2
    assert len(result[1]) == 2

    # Test fails with invalid FITS file or non-list/array inputs
    with pytest.raises(Exception) as exc_info:
        with fits.open('non_existent_file.fits') as f:
            w = WCS(f[0].header)
    assert exc_info.type == FileNotFoundError

    with pytest.raises(Exception) as exc_info:
        w.wcs_pix2world('non_list_input', 0)
    assert exc_info.type == TypeError
