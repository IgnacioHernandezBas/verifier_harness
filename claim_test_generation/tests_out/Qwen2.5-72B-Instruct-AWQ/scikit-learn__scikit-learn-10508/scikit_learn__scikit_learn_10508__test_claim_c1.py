import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1(monkeypatch):
    # GIVEN: A LabelEncoder instance fitted on string labels (e.g., ['a', 'b'])
    le = LabelEncoder()
    le.fit(['a', 'b'])

    # WHEN: calling .transform([]) on the fitted LabelEncoder
    transformed = le.transform([])

    # THEN: returns an empty NumPy array with dtype matching the encoded output
    # Test must verify the output is an empty numpy array.
    assert isinstance(transformed, np.ndarray), "Transformed output is not a numpy array."
    assert transformed.size == 0, "Transformed output is not empty."

    # Test must confirm the dtype of the output array.
    assert transformed.dtype == np.int64, f"Array dtype {transformed.dtype} does not match expected dtype {np.int64}."

    # Test must handle edge cases appropriately.
    # Edge case: Fit on an empty list and then transform an empty list
    le_empty = LabelEncoder()
    le_empty.fit([])
    transformed_empty = le_empty.transform([])
    assert isinstance(transformed_empty, np.ndarray), "Transformed output is not a numpy array."
    assert transformed_empty.size == 0, "Transformed output is not empty."
    assert transformed_empty.dtype == np.int64, f"Array dtype {transformed_empty.dtype} does not match expected dtype {np.int64}."

    # Edge case: Fit on a list with a single unique label and then transform an empty list
    le_single = LabelEncoder()
    le_single.fit(['a'])
    transformed_single = le_single.transform([])
    assert isinstance(transformed_single, np.ndarray), "Transformed output is not a numpy array."
    assert transformed_single.size == 0, "Transformed output is not empty."
    assert transformed_single.dtype == np.int64, f"Array dtype {transformed_single.dtype} does not match expected dtype {np.int64}."

    # Edge case: Fit on a list with mixed types and then transform an empty list
    le_mixed = LabelEncoder()
    le_mixed.fit(['a', 1, 2.0])
    transformed_mixed = le_mixed.transform([])
    assert isinstance(transformed_mixed, np.ndarray), "Transformed output is not a numpy array."
    assert transformed_mixed.size == 0, "Transformed output is not empty."
    assert transformed_mixed.dtype == np.int64, f"Array dtype {transformed_mixed.dtype} does not match expected dtype {np.int64}."
