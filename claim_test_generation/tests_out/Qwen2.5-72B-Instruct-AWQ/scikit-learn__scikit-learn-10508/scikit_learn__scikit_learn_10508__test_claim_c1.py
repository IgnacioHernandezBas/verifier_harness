# Checklist TODO: Fit LabelEncoder with integers and call transform with an empty list.
# Checklist TODO: Verify the output is an empty array with dtype=int64.
# Checklist TODO: Ensure no exceptions are raised during the test.
import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np

def test_claim_c1(tmpdir, monkeypatch, capsys):
    # GIVEN: LabelEncoder is fitted with a list of integers
    le = LabelEncoder()
    le.fit([1, 2])

    # WHEN: transform is called with an empty list
    transformed = le.transform([])

    # THEN: returns an array with size 0
    assert transformed.size == 0, "transform([]) should return an array with size 0"

    # THEN: returns an array with dtype=int64
    assert transformed.dtype == np.int64, "transform([]) should return an array with dtype=int64"

    # THEN: No exceptions are raised during the transform call
    assert not capsys.readouterr().err, "No exceptions should be raised during the transform call"

    # Edge cases
    # Test with an empty list after fitting with a single integer
    le_single = LabelEncoder()
    le_single.fit([1])
    transformed_single = le_single.transform([])
    assert transformed_single.size == 0, "transform([]) should return an array with size 0 after fitting with a single integer"
    assert transformed_single.dtype == np.int64, "transform([]) should return an array with dtype=int64 after fitting with a single integer"

    # Test with an empty list after fitting with a list of strings
    le_strings = LabelEncoder()
    le_strings.fit(["a", "b"])
    transformed_strings = le_strings.transform([])
    assert transformed_strings.size == 0, "transform([]) should return an array with size 0 after fitting with a list of strings"
    assert transformed_strings.dtype == np.int64, "transform([]) should return an array with dtype=int64 after fitting with a list of strings"

    # Test with an empty list without fitting the LabelEncoder
    le_unfitted = LabelEncoder()
    with pytest.raises(ValueError, match="y contains new labels"):
        le_unfitted.transform([])
