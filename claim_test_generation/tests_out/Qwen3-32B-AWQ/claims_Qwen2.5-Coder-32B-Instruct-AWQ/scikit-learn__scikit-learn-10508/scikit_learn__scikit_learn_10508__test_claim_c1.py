# Checklist TODO: LabelEncoder fits on integer list without error
# Checklist TODO: Transform returns empty array when input is empty list
# Checklist TODO: Output array has correct dtype and zero elements
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # Given: LabelEncoder fitted with integers
    le = LabelEncoder()
    le.fit([1, 2])
    
    # When: transform with empty list
    result = le.transform([])
    
    # Then: returns empty array with correct dtype
    assert result.size == 0
    assert result.dtype == np.int64
