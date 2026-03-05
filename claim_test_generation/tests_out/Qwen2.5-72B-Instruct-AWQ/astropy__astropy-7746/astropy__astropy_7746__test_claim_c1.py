import pytest
from astropy.wcs import WCS
from astropy.io import fits
import numpy as np

def test_claim_c1(tmpdir, monkeypatch, capsys):
    # Test must use a valid FITS file for WCS instance.
    fits_file = tmpdir.join('test.fits')
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        f.writeto(fits_file)

    w = WCS(str(fits_file))

    # Test must pass empty lists to wcs_pix2world.
    result = w.wcs_pix2world([], [], 0)

    # Test must verify empty outputs are returned.
    assert isinstance(result, tuple), "Result should be a tuple"
    assert len(result) == 2, "Result should have two elements"
    assert len(result[0]) == 0, "First element should be an empty list or array"
    assert len(result[1]) == 0, "Second element should be an empty list or array"

    # Output types match input types (lists or arrays)
    assert isinstance(result[0], list), "First element should be a list"
    assert isinstance(result[1], list), "Second element should be a list"

    # Output size is 0
    assert len(result[0]) == 0, "First element should be empty"
    assert len(result[1]) == 0, "Second element should be empty"

    # Edge cases
    # Pass non-empty lists with invalid data types
    with pytest.raises(TypeError):
        w.wcs_pix2world(['a'], ['b'], 0)

    # Pass a non-zero third argument with empty lists
    result = w.wcs_pix2world([], [], 1)
    assert len(result[0]) == 0, "First element should be empty"
    assert len(result[1]) == 0, "Second element should be empty"

    # Pass a negative third argument with empty lists
    result = w.wcs_pix2world([], [], -1)
    assert len(result[0]) == 0, "First element should be empty"
    assert len(result[1]) == 0, "Second element should be empty"
