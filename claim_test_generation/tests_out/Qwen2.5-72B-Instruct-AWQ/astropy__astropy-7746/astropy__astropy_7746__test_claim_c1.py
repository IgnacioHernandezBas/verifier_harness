# Checklist TODO: Test must use only public API methods.
# Checklist TODO: Test must verify output is empty and matches input type.
# Checklist TODO: Test must ensure no exceptions are raised.
import pytest
from astropy.wcs import WCS
from astropy.io import fits
import numpy as np

def test_claim_c1(tmpdir, monkeypatch, capsys):
    # Given: A WCS object and empty input lists/arrays
    with fits.open('astropy/wcs/tests/data/sip.fits') as f:
        w = WCS(f[0].header)

    # When: Calling wcs_pix2world with empty lists/arrays as pixel coordinates
    # Then: Returns empty outputs (empty sequences or arrays with size==0) without raising InconsistentAxisTypesError

    # Test with empty numpy array
    inp = np.zeros((0, 2))
    result = w.all_pix2world(inp, 0)
    assert isinstance(result, np.ndarray)
    assert result.shape == (0, 2)

    # Test with empty list
    inp = []
    result = w.all_pix2world(inp, 0)
    assert isinstance(result, list)
    assert len(result) == 0

    # Test with mixed empty and non-empty inputs
    inp = [], [1]
    result = w.all_pix2world(inp[0], inp[1], 0)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert len(result[0]) == 0
    assert len(result[1]) == 0

    # Edge cases
    # Passing None instead of empty list/array
    with pytest.raises(TypeError):
        w.all_pix2world(None, 0)

    # Passing a single value instead of a list/array
    with pytest.raises(ValueError):
        w.all_pix2world(1, 0)

    # Passing a non-empty list/array with invalid values
    with pytest.raises(ValueError):
        w.all_pix2world([1, 2, 3], 0)
