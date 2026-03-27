import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np
from numpy.testing import assert_array_equal

def test_claim_c2():
    # LabelEncoder fits on string list
    le = LabelEncoder()
    le.fit(['apple', 'banana', 'cherry'])
    # Transform called with empty list
    transformed = le.transform([])
    # Output is empty array with correct dtype
    assert transformed.size == 0
    assert transformed.dtype == np.int64
    assert_array_equal(np.array([], dtype=np.int64), transformed)
