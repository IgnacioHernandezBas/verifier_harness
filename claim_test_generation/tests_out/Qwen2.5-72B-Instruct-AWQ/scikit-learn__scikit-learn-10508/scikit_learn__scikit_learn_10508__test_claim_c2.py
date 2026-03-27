import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np

def test_claim_c2(monkeypatch):
    # GIVEN: A LabelEncoder instance fitted on string labels (e.g., ['a', 'b'])
    le = LabelEncoder()
    le.fit(['a', 'b'])

    # WHEN: calling .transform([]) on the fitted LabelEncoder
    transformed = le.transform([])

    # THEN: does not raise a TypeError
    # Test must verify no TypeError is raised.
    with pytest.raises(TypeError, match=None) as exc_info:
        le.transform([])
    assert exc_info.type is not TypeError, "TypeError should not be raised"

    # THEN: The returned array is empty
    # Test must confirm the output is an empty numpy array.
    assert isinstance(transformed, np.ndarray), "Output should be a numpy array"
    assert len(transformed) == 0, "Output array should be empty"

    # THEN: The returned array has the correct dtype
    # Test must validate the dtype of the output array.
    assert transformed.dtype == np.int64, f"Array dtype {transformed.dtype} does not match expected dtype {np.int64}."
