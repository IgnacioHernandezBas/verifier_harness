# Checklist TODO: Test passes with empty input and string labels
# Checklist TODO: Test passes with empty input and non-string labels
# Checklist TODO: Test fails with non-empty input or non-list input
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1(capsys):
    # Given: A LabelEncoder instance fitted on string labels (e.g., ['a', 'b'])
    le = LabelEncoder()
    le.fit(['a', 'b'])

    # When: calling .transform([]) on the fitted LabelEncoder
    transformed = le.transform([])

    # Then: returns an empty NumPy array with dtype matching the encoded output (e.g., int64 for integer inputs, or appropriate dtype for string inputs)
    assert isinstance(transformed, np.ndarray)
    assert len(transformed) == 0
    assert transformed.dtype == np.float64

    # Test passes with empty input and non-string labels
    le.fit([1, 2])
    transformed = le.transform([])
    assert isinstance(transformed, np.ndarray)
    assert len(transformed) == 0
    assert transformed.dtype == np.float64

    # Test fails with non-empty input or non-list input
    with pytest.raises(ValueError):
        le.transform('a')

    with pytest.raises(ValueError):
        le.transform(1)
