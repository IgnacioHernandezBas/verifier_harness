# Checklist TODO: Encoder is properly fitted before transform
# Checklist TODO: Empty input returns zero-length array
# Checklist TODO: Output dtype matches GOLD behavior (float64)
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # GIVEN: LabelEncoder is fitted with certain inputs
    le = LabelEncoder()
    le.fit([1, 2])
    
    # WHEN: transform is called with an empty list
    result = le.transform([])
    
    # THEN: returns empty outputs (empty sequences OR arrays with size==0)
    assert isinstance(result, np.ndarray)
    assert result.shape == (0,)
    assert result.dtype == np.float64
