import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np

def test_claim_c2(capsys):
    # Given: LabelEncoder is fitted with a list of strings.
    le = LabelEncoder()
    le.fit(["1", "2", "1", "2", "2"])

    # When: transform is called with an empty list.
    transformed = le.transform([])

    # Then: returns empty outputs (empty sequences OR arrays with size==0)
    # Test passes with empty list input
    assert len(transformed) == 0

    # Test checks output type and size
    assert isinstance(transformed, np.ndarray)
    assert transformed.size == 0

    # Test does not rely on internal implementation details
    # No internal implementation details are checked in this test

    # Additional edge cases
    # Transform with single-element list
    single_element_transformed = le.transform(["1"])
    assert len(single_element_transformed) == 1

    # Transform with list containing duplicate strings
    duplicate_strings_transformed = le.transform(["1", "2", "1", "2", "2"])
    assert len(duplicate_strings_transformed) == 5

    # Transform with non-string elements in fit data
    le.fit(["1", "2", 1, "2", "2"])
    non_string_elements_transformed = le.transform([])
    assert len(non_string_elements_transformed) == 0
