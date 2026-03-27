# Checklist TODO: Empty input returns empty array after integer fit
# Checklist TODO: Empty input returns empty array after string fit
# Checklist TODO: Transform handles empty input without errors
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # Given: LabelEncoder is fit with a list of integers
    le_int = LabelEncoder()
    le_int.fit([1, 2])
    # When: transform is called with empty list
    result_int = le_int.transform([])
    # Then: returns empty array with size 0
    assert result_int.size == 0  # Output array has size 0
    assert isinstance(result_int, np.ndarray)  # Output is empty array

    # Given: LabelEncoder is fit with a list of strings
    le_str = LabelEncoder()
    le_str.fit(['a', 'b'])
    # When: transform is called with empty list
    result_str = le_str.transform([])
    # Then: returns empty array with size 0
    assert result_str.size == 0  # Output array has size 0
    assert isinstance(result_str, np.ndarray)  # Output is empty array
