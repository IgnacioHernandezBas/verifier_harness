import pytest

from astropy.table import Table


def test_ascii_qdp_accepts_lowercase_commands(tmp_path):
    """
    Claim: ascii.qdp must treat QDP commands case-insensitively.
    The file with 'read serr 1 2' should read into a Table rather than crashing.
    """
    qdp_text = "read serr 1 2\n1 0.5 1 0.5\n"
    p = tmp_path import pytest

from astropy.table import Table


def test_ascii_qdp_accepts_lowercase_commands(tmp_path):
    """
    Claim: ascii.qdp must treat QDP commands case-insensitively.
    The file with 'read serr 1 2' should read into a Table rather than crashing.
    """
    qdp_text = "read serr 1 2\n1 0.5 1 0.5\n"
    p = tmp_path / "test.qdp"
    p.write_text(qdp_text)

    tbl = Table.read(str(p), format="ascii.qdp")

    assert isinstance(tbl, Table)
    assert len(tbl) == 1
/ "test.qdp"
    p.write_text(qdp_text)

    tbl = Table.read(str(p), format="ascii.qdp")

    assert isinstance(tbl, Table)
    assert len(tbl) == 1
