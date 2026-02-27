# Checklist TODO: LabelEncoder returns an empty array for empty input.
# Checklist TODO: Output array has dtype int64.
# Checklist TODO: Test passes with various empty input types.
import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np

def test_claim_c1():
    # Given: LabelEncoder is fitted with a non-empty list of integers.
    le = LabelEncoder()
    le.fit([1, 2])

    # When: transform is called with an empty list.
    transformed_list = le.transform([])

    # Then: The output is an empty array.
    assert len(transformed_list) == 0

    # And: The dtype of the output array is int64.
    assert transformed_list.dtype == np.int64

    # When: transform is called with an empty tuple.
    transformed_tuple = le.transform(())

    # Then: The output is an empty array.
    assert len(transformed_tuple) == 0

    # And: The dtype of the output array is int64.
    assert transformed_tuple.dtype == np.int64

    # When: transform is called with an empty set.
    transformed_set = le.transform(set())

    # Then: The output is an empty array.
    assert len(transformed_set) == 0

    # And: The dtype of the output array is int64.
    assert transformed_set.dtype == np.int64

    # When: transform is called with an empty numpy array.
    transformed_array = le.transform(np.array([]))

    # Then: The output is an empty array.
    assert transformed_array.size == 0

    # And: The dtype of the output array is int64.
    assert transformed_array.dtype == np.int64
