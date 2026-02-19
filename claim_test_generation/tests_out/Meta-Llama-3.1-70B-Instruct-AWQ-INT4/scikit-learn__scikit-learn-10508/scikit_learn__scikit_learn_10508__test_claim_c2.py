import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c2(capsys):
    # GIVEN: LabelEncoder is fitted with certain inputs
    le = LabelEncoder()
    le.fit(["1", "2", "1", "2", "2"])

    # WHEN: transform is called with an empty list
    try:
        transformed = le.transform([])
    except TypeError:
        pytest.fail("Test does not raise a TypeError when transforming an empty list.")

    # THEN: does not raise a TypeError
    # Test checks the shape and type of the transformed array.
    assert isinstance(transformed, np.ndarray), "transformed is not a numpy array"
    assert len(transformed) == 0, "transformed is not an empty array"
    assert transformed.dtype == np.int64, "transformed dtype is not int64"

    # Test handles edge cases with non-empty lists and non-list inputs.
    # Passing a non-empty list to LabelEncoder.transform
    le.transform(["1", "2", "3"])

    # Passing a non-list input to LabelEncoder.transform
    with pytest.raises(TypeError):
        le.transform("1")

    # Fitting LabelEncoder with an empty list
    le.fit([])
