import pytest
from sympy.geometry import Point

def test_claim_c3(tmpdir, monkeypatch, capsys):
    # Import Point from sympy.geometry.
    # Create a Point object at (0, 0).
    p1 = Point(0, 0)
    # Create a scaled Point object at (1, 1) with scale factor 2.
    p2 = Point(1, 1) * 2

    # Create two Point objects and add them.
    try:
        result = p1 + p2
    except Exception as e:
        pytest.fail(f"Exception raised: {e}")

    # Verify no exceptions are raised during addition.
    assert result == Point(2, 2)

    # Test with a scale factor of 0.
    p3 = Point(1, 1) * 0
    try:
        result = p1 + p3
    except Exception as e:
        pytest.fail(f"Exception raised: {e}")

    assert result == Point(1, 1)

    # Test with a scale factor of -1.
    p4 = Point(1, 1) * -1
    try:
        result = p1 + p4
    except Exception as e:
        pytest.fail(f"Exception raised: {e}")

    assert result == Point(-1, -1)

    # Test with non-integer coordinates.
    p5 = Point(0.5, 0.5) * 2
    try:
        result = p1 + p5
    except Exception as e:
        pytest.fail(f"Exception raised: {e}")

    assert result == Point(1, 1)
