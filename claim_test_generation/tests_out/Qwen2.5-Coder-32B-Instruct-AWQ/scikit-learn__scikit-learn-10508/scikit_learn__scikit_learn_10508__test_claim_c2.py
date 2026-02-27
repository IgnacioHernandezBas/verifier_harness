# Checklist TODO: Test passes without raising TypeError
# Checklist TODO: Resulting array is empty
# Checklist TODO: Resulting array dtype is int64
import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np

def test_claim_c2():
    # Given: LabelEncoder is fitted with certain inputs
    le = LabelEncoder()
    le.fit([1, 2])

    # When: transform is called with an empty list
    transformed = le.transform([])

    # Then: does not raise a TypeError
    # Check that no exception is raised
    assert isinstance(transformed, np.ndarray)

    # Then: returns an empty array
    assert transformed.size == 0

    # Then: returned array has dtype int64
    assert transformed.dtype == np.int64

    # Edge case: transform with an empty list after fitting with a single unique value
    le.fit([1])
    transformed = le.transform([])
    assert isinstance(transformed, np.ndarray)
    assert transformed.size == 0
    assert transformed.dtype == np.int64

    # Edge case: transform with an empty list after fitting with multiple unique values
    le.fit([1, 2, 3])
    transformed = le.transform([])
    assert isinstance(transformed, np.ndarray)
    assert transformed.size == 0
    assert transformed.dtype == np.int64

    # Edge case: transform with an empty list after fitting with non-integer values
    le.fit(["a", "b"])
    transformed = le.transform([])
    assert isinstance(transformed, np.ndarray)
    assert transformed.size == 0
    assert transformed.dtype == np.int64
