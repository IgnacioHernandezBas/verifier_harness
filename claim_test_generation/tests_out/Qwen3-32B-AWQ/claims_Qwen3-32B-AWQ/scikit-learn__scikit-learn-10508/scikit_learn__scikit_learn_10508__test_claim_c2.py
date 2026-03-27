# Checklist TODO: LabelEncoder fits on string labels.
# Checklist TODO: Transforming empty list does not raise TypeError.
# Checklist TODO: Returns empty array with dtype=int64.
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c2():
    # Given: LabelEncoder fitted on string labels
    le = LabelEncoder()
    le.fit(['a', 'b'])
    # When: transform empty list
    transformed = le.transform([])
    # Then: no TypeError raised, returns empty array with dtype=int64
    assert len(transformed) == 0
    assert transformed.dtype == np.int64
