import numpy as np
import pytest

from astropy.io.fits import Header
from astropy.wcs import WCS


def _make_minimal_valid_wcs_2d() -> WCS:
    """
    Create a minimal but valid 2D celestial WCS. We avoid external FITS files
    to keep this test self-contained and stable in sandboxed environments.
    """
    hdr = Header()
    hdr["NAXIS"] = 2
    hdr["WCSAXES"] = 2

    # Minimal celestial TAN WCS
    hdr["CTYPE1"] = "RA---TAN"
    hdr["CTYPE2"] = "DEC--TAN"
    hdr["CRVAL1"] = 0.0
    hdr["CRVAL2"] = 0.0
    hdr["CRPIX1"] = 1.0
    hdr["CRPIX2"] = 1.0
    hdr["CDELT1"] = 1.0
    hdr["CDELT2"] = 1.0

    return WCS(hdr)


def test_wcs_pix2world_empty_lists_returns_empty_arrays():
    """
    Claim: WCS.wcs_pix2world must accept empty coordinate arrays/lists and return
    empty outputs (no exception).
    """
    wcs = _make_minimal_valid_wcs_2d()

    ra, dec = wcs.wcs_pix2world([], [], 0)

    assert isinstance(ra, np.ndarray)
    assert isinstance(dec, np.ndarray)
    assert ra.size == 0
    assert dec.size == 0


def test_wcs_pix2world_empty_array_shape_returns_empty_array():
    """
    Same claim, array-form input: an empty (0, 2) array should round-trip to an empty output.
    """
    wcs = _make_minimal_valid_wcs_2d()

    xy = np.empty((0, 2), dtype=float)
    out = wcs.wcs_pix2world(xy, 0)

    assert isinstance(out, np.ndarray)
    assert out.shape == (0, 2)
