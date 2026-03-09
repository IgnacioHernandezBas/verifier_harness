import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1(capsys):
    # Given: LabelEncoder is fitted with a list of integers.
    le = LabelEncoder()
    le.fit([1, 2, 1, 2, 2])

    # When: transform is called with an empty list.
    transformed = le.transform([])

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    # Test passes with empty list input
    assert len(transformed) == 0

    # Test checks output type and shape
    assert isinstance(transformed, np.ndarray)
    assert transformed.size == 0

    # Test does not rely on internal implementation details
    # No internal implementation details are checked in this test

    # Additional tests for edge cases
    # Transform with single-element list
    single_element_transformed = le.transform([1])
    assert len(single_element_transformed) == 1

    # Transform with list containing duplicate values
    duplicate_values_transformed = le.transform([1, 2, 2, 1])
    assert len(duplicate_values_transformed) == 4

    # Transform with non-integer values
    with pytest.raises(ValueError):
        le.transform(['a', 'b', 'a'])
