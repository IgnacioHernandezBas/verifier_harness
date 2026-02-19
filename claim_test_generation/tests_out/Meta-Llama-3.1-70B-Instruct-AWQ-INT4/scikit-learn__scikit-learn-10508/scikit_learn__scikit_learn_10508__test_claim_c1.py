import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1(capsys):
    # Given: LabelEncoder is fitted with certain inputs
    le = LabelEncoder()
    le.fit(["1", "2", "1", "2", "2"])

    # When: transform is called with an empty list
    transformed = le.transform([])

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    assert len(transformed) == 0  # transformed is an empty array
    assert transformed.dtype == np.float64  # transformed has dtype float64

    # Test passes with empty input to transform
    assert len(transformed) == 0

    # transformed array has correct dtype
    assert transformed.dtype == np.float64

    # No errors are raised during test execution
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err

    # Edge case: Passing None as input to transform
    with pytest.raises(ValueError):
        le.transform(None)

    # Edge case: Passing a non-empty list with invalid values to transform
    with pytest.raises(ValueError):
        le.transform(["invalid"])
