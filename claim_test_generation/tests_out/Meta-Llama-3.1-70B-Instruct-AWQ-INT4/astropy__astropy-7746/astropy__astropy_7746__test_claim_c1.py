# Checklist TODO: Test returns empty outputs with empty inputs
# Checklist TODO: Test does not raise exception with empty inputs
# Checklist TODO: Test handles edge cases correctly
import pytest
from astropy.io import fits
from astropy.wcs import WCS

def test_claim_c1(capsys):
    # Given: An instance of WCS is created from a valid FITS file and empty lists/arrays are passed to the `wcs_pix2world` method.
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        wcs = WCS(f[0].header)

    # When: wcs.wcs_pix2world([], [], 0) is called
    result = wcs.wcs_pix2world([], [], 0)

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    assert len(result) == 2
    assert len(result[0]) == 0
    assert len(result[1]) == 0

    # Test does not raise exception with empty inputs
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''

    # Test handles edge cases correctly
    # Passing non-empty lists/arrays
    result = wcs.wcs_pix2world([1, 2], [3, 4], 0)
    assert len(result) == 2
    assert len(result[0]) == 2
    assert len(result[1]) == 2

    # Passing non-list/array inputs
    with pytest.raises(TypeError):
        wcs.wcs_pix2world('a', 'b', 0)

    # Passing invalid FITS file
    with pytest.raises(IOError):
        with fits.open('invalid.fits') as f:
            WCS(f[0].header)
