# Checklist TODO: Fit LabelEncoder on string array ['a', 'b']
# Checklist TODO: Call .transform([]) without raising TypeError
# Checklist TODO: Verify output array has integer dtype
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c2():
    # GIVEN: Create LabelEncoder instance and fit on ['a', 'b']
    le = LabelEncoder()
    le.fit(['a', 'b'])
    # WHEN: Call .transform([]) on the fitted encoder
    result = le.transform([])
    # THEN: Does not raise TypeError
    # Verify output array has integer dtype
    assert np.issubdtype(result.dtype, np.integer)
