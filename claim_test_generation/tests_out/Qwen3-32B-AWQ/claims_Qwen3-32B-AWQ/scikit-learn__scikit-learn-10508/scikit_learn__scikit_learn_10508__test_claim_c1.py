# Checklist TODO: Test returns empty array for empty input
# Checklist TODO: Verify dtype matches GOLD run (float64)
# Checklist TODO: Ensure no value errors for empty input
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # Given: LabelEncoder fitted on string labels
    le = LabelEncoder()
    le.fit(['a', 'b'])
    
    # When: Transform empty input
    result = le.transform([])
    
    # Then: Verify empty array with correct dtype
    assert isinstance(result, np.ndarray)
    assert result.shape == (0,)
    assert result.dtype == np.float64
