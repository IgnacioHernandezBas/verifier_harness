# Checklist TODO: Verify empty array is returned for empty input
# Checklist TODO: Confirm dtype matches encoded output (float64 for string fit in GOLD case)
# Checklist TODO: Ensure no exceptions raised during transform
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # Given: LabelEncoder fitted on string labels
    le = LabelEncoder()
    le.fit(['a', 'b'])
    # When: transform empty list
    result_str = le.transform([])
    # Then: returns empty numpy array with dtype=float64
    assert isinstance(result_str, np.ndarray)
    assert result_str.shape == (0,)
    assert result_str.dtype == np.float64
