# Checklist TODO: Fit encoder with [1,2] then transform empty list
# Checklist TODO: Verify no TypeError occurs during transformation
# Checklist TODO: Confirm resulting array has correct dtype=int64
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c2():
    # GIVEN: LabelEncoder is fitted with string inputs
    le = LabelEncoder()
    le.fit(["1", "2"])
    # WHEN: transform is called with an empty list
    transformed = le.transform([])
    # THEN: No TypeError is raised, output is numpy array with dtype=int64
    assert isinstance(transformed, np.ndarray)
    assert transformed.dtype == np.int64
    assert transformed.size == 0
    # Confirm LabelEncoder instance remains valid
    assert hasattr(le, "classes_")
    assert np.array_equal(le.classes_, np.array(["1", "2"]))
